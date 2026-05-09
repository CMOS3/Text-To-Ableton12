import asyncio
import ast
import json
import os
import inspect
import traceback
from typing import Optional, List, Dict, Any, AsyncGenerator

from google import genai
from google.genai import types

from backend.gemini.retriever import RetrieverAgent
from backend.gemini.tools import AbletonToolMixin
from backend.logger import get_json_logger

logger = get_json_logger(__name__)

class CreativePlannerAgent(AbletonToolMixin):
    """
    Main orchestration agent (Single-Shot Compiler / Supervisor) that communicates
    with the Gemini API, maintains the conversation history, and invokes
    Ableton tools or the Retriever for RAG.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment. Please provide it in the Application Settings UI."
            )

        self.client = genai.Client(api_key=api_key)
        self.retriever = RetrieverAgent(api_key=api_key)

        self.pro_model = "models/gemini-3.1-pro-preview-customtools"
        self.approval_event = asyncio.Event()
        self.is_approved = False

        # Tools to expose to the LLM
        self.tools = [
            self.fetch_resource,
            self.create_midi_track,
            self.set_track_name,
            self.set_clip_name,
            self.load_instrument_or_effect,
            self.load_drum_kit,
            self.mix_track,
            self.inject_midi_to_new_clip,
            self.set_device_parameter_batch,
            self.search_device_parameters,
        ]

        self.system_instruction = (
            "ROLE & TONE: You are a senior Ableton Live technical consultant and mixing engineer. Speak professionally, clinically, and concisely. "
            "You will be provided with a 'Genre/Style' context. Use this genre strictly for your musical decisions (chords, device selection, sound design). "
            "DO NOT adopt the genre as a conversational persona.\n\n"
            "FORMATTING: Your text responses must ALWAYS be cleanly formatted using Markdown. Use bold headers and bulleted lists to organize your execution summaries.\n\n"
            "MANUAL ACTIONS: You must ALWAYS include a bulleted '### Manual Actions Required' section in your `ui_text_response` to guide the user on tweaking secondary parameters, placing samples, or assigning macros that you chose not to map programmatically.\n\n"
            "SOUND DESIGN & MULTI-TURN RAG WORKFLOW:\n"
            "- If the user asks you to load a native Ableton device AND configure it, you MUST use a multi-turn approach:\n"
            "  * TURN 1 (Context Gathering): Output a JSON array containing ONLY `search_device_parameters` to learn the exact parameter names based on your creative intent. DO NOT include any mutations (like creating tracks or loading devices) in Turn 1! If you include a mutation, the execution loop will prematurely break and you will fail the configuration.\n"
            "  * TURN 2 (Execution): The system will feed the parameter bounds back to you. Now, output your final JSON array containing `create_midi_track` (if needed), `load_instrument_or_effect`, `set_device_parameter_batch` (using the exact Retriever strings), and `ui_text_response`.\n"
            "- Do not guess parameter names! You MUST use the exact internal names and respect the min/max bounds returned by the Retriever.\n"
            "- Ableton parameters are often normalized to floats between 0.0 and 1.0. Mathematically scale your desired value into this bounds range.\n\n"
            "MIDI GENERATION:\n"
            "- To generate MIDI, use `inject_midi_to_new_clip` and populate the `notes` array directly.\n"
            "- You MUST use valid semantic pitch names for notes (e.g., 'C1', 'F#2', 'Bb-1').\n"
            "- Ableton length and time values are strictly in BEATS, not bars! If the user asks for a 4-bar loop in 4/4 time, you MUST set length to 16.0. 1 Bar = 4.0 Beats.\n\n"
            "CLIP NAMING:\n"
            "- Whenever you use `create_clip` or `inject_midi_to_new_clip`, you MUST always provide a descriptive `clip_name` argument based on the musical intent.\n\n"
            "You have access to a suite of Ableton proxy tools to control the session.\n"
            "You MUST output exactly ONE valid JSON array containing a sequential script of actions.\n"
            "Example format:\n"
            "[\n"
            '   {"tool": "create_midi_track", "args": {"track_name": "Drums"}},\n'
            '   {"tool": "ui_text_response", "args": {"text": "I have created your Drums track."}}\n'
            "]\n"
            "CRITICAL: If you create a new track, you must calculate its new `track_index` for subsequent tools. The new index is ALWAYS equal to the current total number of tracks in the session (e.g., if the provided session state shows 4 existing tracks [indexes 0,1,2,3], the newly created track will be index 4).\n"
            "CRITICAL: DO NOT HALLUCINATE TOOL NAMES. You must ONLY use the exact tool names provided in the minified JSON schemas below. Do not invent tools like 'load_device_to_track_by_name'. If a tool requires a `track_index`, you MUST use the integer index.\n"
            "If the user asks for advice, sound design guidance, or plain text communication, you MUST use the synthetic tool `ui_text_response` and provide the text in its `text` argument. Use Markdown within this text.\n"
            "DO NOT wrap your JSON in markdown code blocks. NO backticks. Output valid JSON array only.\n"
            "Here are the available target tools mapped as minified JSON:\n"
            + json.dumps(self._generate_minified_schemas(), separators=(",", ":"))
        )

    async def search_device_parameters(self, device_name: str, intent: str) -> str:
        """[RAG TOOL] Semantically searches for parameter names and value bounds for a specific device based on your musical intent."""
        return await self.retriever.search_catalog(device_name, intent)

    async def chat(
        self, user_prompt: str, chat_history: Optional[List[Dict[str, Any]]] = None, require_approval: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Executes a Single-Shot Compiler agent to fulfill the prompt.
        Yields JSON strings representing the status or final result.
        """
        self.approval_event.clear()
        self.is_approved = False
        self.retriever.prompt_tokens = 0
        self.retriever.candidate_tokens = 0

        if chat_history is None:
            chat_history = []

        total_prompt_tokens = 0
        total_candidate_tokens = 0
        models_used_chain = ["Gemini 3.1 Pro (Single-Shot Compiler)"]

        contents = []
        final_user_text = user_prompt
        history_len = len(chat_history)

        for i, msg in enumerate(chat_history):
            role = (
                "model" if msg.get("role", "").lower() in ["assistant", "ai", "model"] else "user"
            )
            content_text = msg.get("content", "")

            if i == history_len - 1 and role == "user":
                if content_text:
                    final_user_text = content_text
                continue

            if content_text:
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=content_text)])
                )

        yield (
            json.dumps({"type": "status", "message": "Pre-fetching session state locally..."})
            + "\n"
        )
        await asyncio.sleep(0.01)

        try:
            session_state = await asyncio.to_thread(self.fetch_resource, "ableton://session/state")
        except Exception as e:
            logger.warning("Failed to pre-fetch session", extra={"extra_data": {"error": str(e)}})
            session_state = f"Failed to pre-fetch session: {e}"

        augmented_prompt = f"LOCAL SESSION STATE:\n{session_state}\n\nUSER PROMPT:\n{final_user_text}\n\nNOTE: If you need more track details to execute the intent, output ONLY `fetch_resource` actions first. The system will run them and return the results so you can decide the final actions."
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=augmented_prompt)])
        )

        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=0.0,
            response_mime_type="application/json",
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        yield json.dumps({"type": "status", "message": "Supervisor analyzing..."}) + "\n"
        await asyncio.sleep(0.01)

        turn_count = 0
        max_turns = 4
        script_actions = []

        while turn_count < max_turns:
            turn_count += 1
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.pro_model, contents=contents, config=config  # type: ignore
                )
            except Exception as e:
                tb_str = traceback.format_exc()
                logger.error("Gemini API Error", exc_info=True)
                yield (
                    json.dumps({"type": "debug", "content": f"GEMINI_API_ERROR:\n{tb_str}"}) + "\n"
                )
                yield (
                    json.dumps(
                        {
                            "type": "final",
                            "data": {
                                "response": f"System error communicating with Gemini API: {e}",
                                "model_used": "\n".join(models_used_chain),
                                "input_tokens": total_prompt_tokens,
                                "output_tokens": total_candidate_tokens,
                            },
                        }
                    )
                    + "\n"
                )
                return

            if response.usage_metadata:
                total_prompt_tokens += getattr(response.usage_metadata, "prompt_token_count", 0)
                total_candidate_tokens += getattr(
                    response.usage_metadata, "candidates_token_count", 0
                )

            if not response.text:
                logger.error("Empty response from Gemini PRO.")
                yield (
                    json.dumps(
                        {
                            "type": "final",
                            "data": {
                                "response": "Error: Empty response from model.",
                                "model_used": "\n".join(models_used_chain),
                                "input_tokens": total_prompt_tokens,
                                "output_tokens": total_candidate_tokens,
                            },
                        }
                    )
                    + "\n"
                )
                return

            logger.info("Received payload from LLM", extra={"extra_data": {"turn": turn_count, "payload_len": len(response.text)}})

            raw_text = response.text.strip()
            start_idx = raw_text.find("[")

            clean_text = raw_text
            if start_idx != -1:
                in_string = False
                escape = False
                depth = 0
                end_idx = -1

                for i in range(start_idx, len(raw_text)):
                    char = raw_text[i]
                    if escape:
                        escape = False
                    elif char == "\\":
                        escape = True
                    elif char == '"':
                        in_string = not in_string
                    elif not in_string:
                        if char == "[":
                            depth += 1
                        elif char == "]":
                            depth -= 1
                            if depth == 0:
                                end_idx = i
                                break

                if end_idx != -1:
                    clean_text = raw_text[start_idx : end_idx + 1]
                else:
                    fallback_end = raw_text.rfind("]")
                    if fallback_end >= start_idx:
                        clean_text = raw_text[start_idx : fallback_end + 1]

                try:
                    script_actions = json.loads(clean_text)
                    if not isinstance(script_actions, list):
                        script_actions = [script_actions]
                except json.JSONDecodeError as e:
                    logger.error("JSON Decode Error on Planner payload", extra={"extra_data": {"raw": response.text}})
                    yield (
                        json.dumps(
                            {
                                "type": "final",
                                "data": {
                                    "response": f"Error decoding model JSON output: {e}\nRaw output: {response.text}",
                                    "model_used": "\n".join(models_used_chain),
                                    "input_tokens": total_prompt_tokens,
                                    "output_tokens": total_candidate_tokens,
                                },
                            }
                        )
                        + "\n"
                    )
                    return

                has_mutations = any(
                    a.get("tool")
                    not in ["fetch_resource", "ui_text_response", "search_device_parameters"]
                    for a in script_actions
                )
                has_fetches = any(
                    a.get("tool") in ["fetch_resource", "search_device_parameters"]
                    for a in script_actions
                )

                if not has_mutations and has_fetches:
                    fetch_results = []
                    for action in script_actions:
                        if action.get("tool") == "fetch_resource":
                            uri = action.get("args", {}).get("uri", "")
                            if uri:
                                yield (
                                    json.dumps(
                                        {
                                            "type": "status",
                                            "message": f"Supervisor fetching {uri}...",
                                        }
                                    )
                                    + "\n"
                                )
                                res = await asyncio.to_thread(self.fetch_resource, uri)
                                fetch_results.append(f"Result for {uri}:\n{res}")
                        elif action.get("tool") == "search_device_parameters":
                            d_name = action.get("args", {}).get("device_name", "")
                            intent = action.get("args", {}).get("intent", "")
                            yield (
                                json.dumps(
                                    {
                                        "type": "status",
                                        "message": f"RAG Search: {d_name} -> '{intent}'...",
                                    }
                                )
                                + "\n"
                            )
                            res = await self.search_device_parameters(d_name, intent)
                            fetch_results.append(f"Result for RAG search '{d_name}':\n{res}")

                    if response.candidates and len(response.candidates) > 0:
                        if response.candidates[0].content:
                            contents.append(response.candidates[0].content)
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text="\n\n".join(fetch_results))],
                        )
                    )
                    continue

                break

        if require_approval:
            yield json.dumps({"type": "approval_required", "actions": script_actions}) + "\n"
            await self.approval_event.wait()

            if not getattr(self, "is_approved", False):
                logger.info("Execution cancelled by user")
                yield (
                    json.dumps(
                        {
                            "type": "final",
                            "data": {
                                "response": "Execution cancelled by user.",
                                "model_used": "\n".join(models_used_chain),
                                "input_tokens": total_prompt_tokens,
                                "output_tokens": total_candidate_tokens,
                            },
                        }
                    )
                    + "\n"
                )
                return

        yield (
            json.dumps(
                {"type": "status", "message": f"Executing {len(script_actions)} actions locally..."}
            )
            + "\n"
        )
        await asyncio.sleep(0.01)

        responses_accumulated = []
        for i, action in enumerate(script_actions):
            tool_name = action.get("tool")
            args = action.get("args", {})

            if not tool_name:
                continue

            logger.info("Executing Tool", extra={"extra_data": {"tool": tool_name}})
            yield (
                json.dumps(
                    {
                        "type": "status",
                        "message": f"Executing {i + 1}/{len(script_actions)}: {tool_name}...",
                    }
                )
                + "\n"
            )
            await asyncio.sleep(0.01)

            if tool_name == "ui_text_response":
                text_content = args.get("text", "")
                responses_accumulated.append(text_content)
                continue

            if hasattr(self, tool_name):
                method = getattr(self, tool_name)
                try:
                    if inspect.iscoroutinefunction(method):
                        res = await method(**args)
                    else:
                        res = await asyncio.to_thread(method, **args)

                    if isinstance(res, str) and res.strip().startswith("{") and "'" in res:
                        try:
                            res = ast.literal_eval(res)
                        except Exception:
                            pass

                    if tool_name in ["set_device_parameter_batch", "inject_midi_to_new_clip"]:
                        yield (
                            json.dumps({"type": "status", "message": f"Action Result:\n{res}"})
                            + "\n"
                        )

                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error("Tool execution failed", exc_info=True, extra={"extra_data": {"tool": tool_name}})
                    yield (
                        json.dumps({"type": "status", "message": f"Error in {tool_name}: {e}"})
                        + "\n"
                    )
            else:
                error_msg = f"Hallucinated Tool Error: The LLM attempted to call a non-existent tool '{tool_name}'."
                logger.error(error_msg)
                yield json.dumps({"type": "status", "message": error_msg}) + "\n"

        final_text = (
            "\n\n".join(responses_accumulated)
            if responses_accumulated
            else "Tasks executed successfully."
        )

        yield (
            json.dumps(
                {
                    "type": "final",
                    "data": {
                        "response": final_text,
                        "model_used": "PRO_AND_FLASH",
                        "pro_input_tokens": total_prompt_tokens,
                        "pro_output_tokens": total_candidate_tokens,
                        "flash_input_tokens": self.retriever.prompt_tokens,
                        "flash_output_tokens": self.retriever.candidate_tokens,
                    },
                }
            )
            + "\n"
        )
