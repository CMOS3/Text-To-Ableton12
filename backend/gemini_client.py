import os
import json
import logging
import asyncio
import re
import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

from .mcp_proxy import proxy
from . import schema

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GeminiAbletonClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        print(f"DEBUG: GEMINI_API_KEY found: {bool(api_key)}")
        
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment. Please ensure you have a '.env' file "
                "in the project root directory with 'GEMINI_API_KEY=your_key_here'."
            )
        
        self.client = genai.Client(api_key=api_key)
        
        self.system_instruction = (
            "You are a session-aware Ableton expert. You have access to a full suite of Ableton Live tools. "
            "You can control transport, tracks, clips, and the browser. "
            "Always try to gather context (like session info or browser trees) before making destructive or complex actions, "
            "unless the user is explicitly specific. For `add_notes_to_clip`, make sure to pass a structured list of properties. "
            "When asked to create a clip or generate notes, you MUST call `get_song_scale` first to establish the `root_note` and `scale_name`. Use this as your musical foundation. "
            "CRITICAL RULE: You MUST prioritize Compound Tools (like get_session_mix_status) over atomic tools to gather bulk data. "
            "Do not iterate through individual tracks to check states if a single bulk tool exists. "
            "CRITICAL TIME RULE: Ableton length and time values are strictly in BEATS, not bars! "
            "If the user asks for a 4-bar loop in 4/4 time, you MUST set length to 16.0. 1 Bar = 4.0 Beats."
        )
        
        self.pro_model = "models/gemini-3.1-pro-preview-customtools"
        self.flash_model = "models/gemini-3.1-flash-lite-preview"
        
        # Tools to expose to the LLM
        self.tools = [
            self.test_ableton_connection,
            self.get_song_scale,
            self.get_session_info,
            self.set_tempo,
            self.start_playback,
            self.stop_playback,
            self.get_track_info,
            self.create_midi_track,
            self.set_track_name,
            self.select_track,
            self.arm_track,
            self.create_clip,
            self.set_clip_name,
            self.add_notes_to_clip,
            self.fire_clip,
            self.stop_clip,
            self.get_browser_tree,
            self.get_browser_items_at_path,
            self.load_instrument_or_effect,
            self.load_drum_kit,
            self.get_notes_from_clip,
            self.delete_notes_from_clip,
            self.delete_track,
            self.delete_clip,
            self.get_device_parameters,
            self.set_device_parameters,
            self.set_track_volume_by_name,
            self.load_device_to_track_by_name,
            self.generate_named_midi_pattern,
            self.get_session_mix_status,
            self.inject_midi_to_new_clip
        ]

    # --- Core Toolset Implementations ---

    def _execute_proxy_request(self, command: str, **kwargs):
        res = proxy.request_state(command, kwargs if kwargs else None)
        print(f"DEBUG - RAW PROXY RESPONSE ({command}): {res}")
        
        if res.get("status") != "success":
            raise Exception(f"Ableton Proxy Error: {res.get('status')} - {res.get('message', '')}")
            
        data = res.get("data", {})
        if isinstance(data, dict) and "error" in data:
            raise Exception(f"Ableton Error: {data['error']}")
            
        if isinstance(data, dict) and "result" in data:
            return data["result"]
            
        return data


    def test_ableton_connection(self) -> str:
        """Attempts to send a JSON 'ping' message to the Ableton Server."""
        res = self._execute_proxy_request("ping")
        return str(res)

    def get_song_scale(self) -> str:
        """Retrieves whether Scale Mode is active, the root note, and the scale name (e.g. Minor, Major)."""
        return str(self._execute_proxy_request("get_song_scale"))

    def get_session_info(self) -> str:
        """Retrieves the current tracks and state in the Ableton Live session."""
        res = self._execute_proxy_request("get_session_info")
        return str(res)

    def set_tempo(self, tempo: float) -> str:
        """Sets the tempo (BPM) of the Ableton session."""
        try:
            req = schema.TempoRequest(tempo=tempo)
            return str(self._execute_proxy_request("set_tempo", **req.model_dump()))
        except ValidationError as e:
            return f"Validation error: {e}"

    def start_playback(self) -> str:
        """Starts playback in Ableton."""
        return str(self._execute_proxy_request("start_playback"))

    def stop_playback(self) -> str:
        """Stops playback in Ableton."""
        return str(self._execute_proxy_request("stop_playback"))

    def get_track_info(self, track_index: int) -> str:
        """Gets detailed info about a specific track by its integer index (0-indexed)."""
        return str(self._execute_proxy_request("get_track_info", **{"track_index": track_index}))

    def create_midi_track(self, track_name: str) -> str:
        """Creates a new MIDI track in Ableton Live."""
        try:
            req = schema.TrackNameRequest(track_name=track_name)
            return str(self._execute_proxy_request("create_midi_track", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def set_track_name(self, track_index: int, name: str) -> str:
        """Sets the name of a specific track."""
        try:
            req = schema.TrackIndexNameRequest(track_index=track_index, name=name)
            return str(self._execute_proxy_request("set_track_name", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def select_track(self, track_name: str) -> str:
        """Selects (focuses) a track by name."""
        return str(self._execute_proxy_request("select_track", **{"track_name": track_name}))

    def arm_track(self, track_name: str, arm: bool = True) -> str:
        """Arms or disarms a track for recording by name."""
        try:
            req = schema.TrackArmRequest(track_name=track_name, arm=arm)
            return str(self._execute_proxy_request("arm_track", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def create_clip(self, track_index: int, clip_slot_index: int, length: float) -> str:
        """Creates a new MIDI clip in a specific track and clip slot."""
        try:
            req = schema.CreateClipRequest(track_index=track_index, clip_slot_index=clip_slot_index, length=length)
            return str(self._execute_proxy_request("create_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def set_clip_name(self, track_index: int, clip_slot_index: int, name: str) -> str:
        """Sets the name of an existing clip."""
        try:
            req = schema.SetClipNameRequest(track_index=track_index, clip_slot_index=clip_slot_index, name=name)
            return str(self._execute_proxy_request("set_clip_name", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def add_notes_to_clip(self, track_index: int, clip_slot_index: int, notes: list[schema.NoteSchema]) -> str:
        """Adds MIDI notes to a clip using semantic pitch names (e.g. 'C3', 'Eb2')."""
        try:
            processed_notes = []
            for n in notes:
                if hasattr(n, "model_dump"):
                    note_dict = n.model_dump()
                elif isinstance(n, dict):
                    note_dict = n.copy()
                else:
                    note_dict = getattr(n, "__dict__", {}).copy()
                    
                pitch_name = note_dict.get("pitch_name")
                if not pitch_name:
                    return "Error: Missing 'pitch_name' in note payload. You must provide semantic pitch names."
                
                try:
                    midi_val = self._pitch_name_to_midi(pitch_name)
                except ValueError as ve:
                    return f"Error with pitch '{pitch_name}': {ve}"
                    
                note_dict["pitch"] = midi_val
                processed_notes.append(note_dict)

            valid_notes = [schema.NoteSchema(**n) for n in processed_notes]
            req = schema.AddNotesRequest(track_index=track_index, clip_slot_index=clip_slot_index, notes=valid_notes)
            return str(self._execute_proxy_request("add_notes_to_clip", **req.model_dump()))
        except Exception as e:
            return f"Error adding notes: {e}"

    def fire_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Fires (plays) a specific clip."""
        try:
            req = schema.ClipActionRequest(track_index=track_index, clip_slot_index=clip_slot_index)
            return str(self._execute_proxy_request("fire_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def stop_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Stops playback of a specific clip."""
        try:
            req = schema.ClipActionRequest(track_index=track_index, clip_slot_index=clip_slot_index)
            return str(self._execute_proxy_request("stop_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def get_browser_tree(self) -> str:
        """Retrieves the root level tree of the Ableton Live browser."""
        return str(self._execute_proxy_request("get_browser_tree"))

    def get_browser_items_at_path(self, path: str) -> str:
        """Retrieves a list of children items and folders at a specific path in the Ableton Live browser. Use this to dive deeper into folders."""
        try:
            req = schema.BrowserItemsRequest(path=path)
            return str(self._execute_proxy_request("get_browser_items_at_path", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def inject_midi_to_new_clip(self, track_index: int, length: float, notes: list[schema.NoteSchema]) -> str:
        """Finds the first empty clip slot on the track, creates a clip of the specified length, and injects the semantic notes."""
        try:
            processed_notes = []
            for n in notes:
                if hasattr(n, "model_dump"):
                    note_dict = n.model_dump()
                elif isinstance(n, dict):
                    note_dict = n.copy()
                else:
                    note_dict = getattr(n, "__dict__", {}).copy()
                    
                pitch_name = note_dict.get("pitch_name")
                if not pitch_name:
                    return "Error: Missing 'pitch_name' in note payload. You must provide semantic pitch names."
                
                try:
                    midi_val = self._pitch_name_to_midi(pitch_name)
                except ValueError as ve:
                    return f"Error with pitch '{pitch_name}': {ve}"
                    
                note_dict["pitch"] = midi_val
                processed_notes.append(note_dict)

            valid_notes = [schema.NoteSchema(**n) for n in processed_notes]
            req = schema.InjectMidiRequest(track_index=track_index, length=length, notes=valid_notes)
            return str(self._execute_proxy_request("inject_midi_to_new_clip", **req.model_dump()))
        except Exception as e:
            return f"Error injecting midi: {e}"

    def load_instrument_or_effect(self, track_index: int, browser_path: str) -> str:
        """Loads a device (instrument or effect) onto a track from the browser."""
        try:
            req = schema.LoadDeviceRequest(track_index=track_index, browser_path=browser_path)
            return str(self._execute_proxy_request("load_instrument_or_effect", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def load_drum_kit(self, track_index: int, drum_kit_path: str) -> str:
        """Loads a drum kit onto a track."""
        try:
            req = schema.LoadDrumKitRequest(track_index=track_index, drum_kit_path=drum_kit_path)
            return str(self._execute_proxy_request("load_drum_kit", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def get_notes_from_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Retrieves an array of all notes in a specific clip."""
        try:
            req = schema.ClipActionRequest(track_index=track_index, clip_slot_index=clip_slot_index)
            return str(self._execute_proxy_request("get_notes_from_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def delete_notes_from_clip(self, track_index: int, clip_slot_index: int, notes: list[schema.NoteSchema]) -> str:
        """Deletes specific notes from a clip based on precisely matching both pitch and start_time."""
        try:
            valid_notes = [schema.NoteSchema(**n) if isinstance(n, dict) else n for n in notes]
            req = schema.DeleteNotesRequest(track_index=track_index, clip_slot_index=clip_slot_index, notes=valid_notes)
            return str(self._execute_proxy_request("delete_notes_from_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def delete_track(self, track_index: int) -> str:
        """Deletes a track by its integer index."""
        try:
            req = schema.TrackIndexRequest(track_index=track_index)
            return str(self._execute_proxy_request("delete_track", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def delete_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Deletes a clip from a specific track and slot index."""
        try:
            req = schema.ClipActionRequest(track_index=track_index, clip_slot_index=clip_slot_index)
            return str(self._execute_proxy_request("delete_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def get_device_parameters(self, track_index: int, device_index: int) -> str:
        """Gets all parameters for a device on a track to discover their parameter_index. You MUST use this before set_device_parameters."""
        try:
            req = schema.DeviceIndexRequest(track_index=track_index, device_index=device_index)
            return str(self._execute_proxy_request("get_device_parameters", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def set_device_parameters(self, track_index: int, device_index: int, parameter_index: int, value: float) -> str:
        """Sets the numeric value of a specific parameter index on a device."""
        try:
            req = schema.SetDeviceParameterRequest(track_index=track_index, device_index=device_index, parameter_index=parameter_index, value=value)
            return str(self._execute_proxy_request("set_device_parameters", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    # --- Helper Algorithms ---
    def _pitch_name_to_midi(self, pitch_name: str) -> int:
        import re
        notes = {
            'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
            'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
        }
        match = re.match(r"^([A-Ga-g][#b]?)(-?\d+)$", str(pitch_name).strip())
        if not match:
            raise ValueError(f"Invalid pitch name format: {pitch_name}. Expected format like 'C3', 'Eb2'.")
            
        note_str = match.group(1).capitalize()
        octave = int(match.group(2))
        
        if note_str not in notes:
            raise ValueError(f"Invalid note name: {note_str} in {pitch_name}.")
            
        midi = notes[note_str] + (octave + 2) * 12
        if not (0 <= midi <= 127):
            raise ValueError(f"Pitch {pitch_name} translates to {midi}, which is out of MIDI range (0-127).")
        return midi

    # --- Compound Tools ---
    def _get_track_index_by_name(self, track_name: str) -> int:
        try:
            res = self._execute_proxy_request("get_session_info")
            tracks = res.get("tracks", [])
            for i, trk in enumerate(tracks):
                if trk.get("name") == track_name:
                    return i
        except Exception:
            pass
        return -1

    def set_track_volume_by_name(self, track_name: str, gain_db: float) -> str:
        """[COMPOUND TOOL - PREFERRED] Sets the volume of a track by its name in dB."""
        try:
            track_index = self._get_track_index_by_name(track_name)
            if track_index == -1:
                return f"Error: Track '{track_name}' not found."
            return str(self._execute_proxy_request("set_track_volume", **{"track_index": track_index, "volume": gain_db}))
        except Exception as e:
            return str(e)

    def load_device_to_track_by_name(self, track_name: str, device_name: str) -> str:
        """[COMPOUND TOOL - PREFERRED] Loads a device onto a track, both specified by name."""
        try:
            track_index = self._get_track_index_by_name(track_name)
            if track_index == -1:
                return f"Error: Track '{track_name}' not found."
            return self.load_instrument_or_effect(track_index, device_name)
        except Exception as e:
            return str(e)

    def generate_named_midi_pattern(self, track_name: str, clip_name: str, clip_length_bars: float, notes_array: list[dict]) -> str:
        """[COMPOUND TOOL - PREFERRED] Creates a clip, names it, and populates it with MIDI notes in one step. Notes are routed through add_notes_to_clip for Scale-Aware snapping."""
        try:
            track_index = self._get_track_index_by_name(track_name)
            if track_index == -1:
                return f"Error: Track '{track_name}' not found."
            
            session = self._execute_proxy_request("get_session_info")
            tracks = session.get("tracks", [])
            if not tracks:
                return "Error retrieving session info properly, or no tracks."
                
            clip_slots = tracks[track_index].get("clip_slots", [])
            open_slot = next((i for i, slot in enumerate(clip_slots) if not slot.get("has_clip")), -1)
            
            if open_slot == -1:
                return "Error: No open clip slots found on this track."
                
            self.create_clip(track_index, open_slot, clip_length_bars * 4.0)
            self.set_clip_name(track_index, open_slot, clip_name)
            # Snapping is delegated to add_notes_to_clip
            return self.add_notes_to_clip(track_index, open_slot, notes_array)
        except Exception as e:
            return str(e)

    def get_session_mix_status(self) -> str:
        """[COMPOUND TOOL - PREFERRED] Retrieves a summary of volume/gain status for all tracks in the session in one go."""
        try:
            res = self._execute_proxy_request("get_session_info")
            
            tracks = res.get("tracks", [])
            status_lines = []
            for i, trk in enumerate(tracks):
                name = trk.get("name", "Unnamed")
                volume = trk.get("volume", "---")
                panning = trk.get("panning", "---")
                
                if isinstance(volume, (int, float)):
                    volume = f"{volume:.1f}"
                if isinstance(panning, (int, float)):
                    panning = f"{panning:.2f}"
                    
                status_lines.append(f"Track {i} ({name}): Vol={volume}dB | Pan={panning}")
            
            return "\n".join(status_lines) if status_lines else "No tracks found."
        except Exception as e:
            return str(e)

    # --- Chat Engine ---

    async def _route_intent(self, prompt: str):
        """Determines if the prompt is simple enough for Ollama, otherwise falls back to Gemini Flash, then Pro."""
        system_instruction_ollama = (
            "You are an intent classifier for an Ableton DAW assistant. "
            "Analyze the user's prompt. "
            "If the prompt EXACTLY maps to one of these three atomic tools: "
            "1) set_tempo (requires 'tempo' float) "
            "2) start_playback (no params) "
            "3) stop_playback (no params) "
            "Output ONLY a strict JSON payload representing the tool name and its parameters. "
            "Example 1: {\"tool\": \"set_tempo\", \"payload\": {\"tempo\": 120.0}} "
            "Example 2: {\"tool\": \"start_playback\", \"payload\": {}} "
            "If the prompt requires creative reasoning, track changes, clip generation, or ANYTHING "
            "outside of those 3 atomic transport commands, output EXACTLY the phrase: "
            "STATUS: COMPLEX\n"
            "DO NOT use Markdown, bolding, asterisks, or code blocks. Output raw text or raw JSON only."
        )

        ollama_payload = {
            "model": "gemma4:e4b",
            "prompt": prompt,
            "system": system_instruction_ollama,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post("http://localhost:11434/api/generate", json=ollama_payload)
                res.raise_for_status()
                data = res.json()
                result_text = data.get("response", "").strip()

                yield {"type": "debug", "content": f"RAW_OLLAMA_RESPONSE:\n{result_text}"}

                clean_json = re.sub(r'^```json\s*', '', result_text, flags=re.MULTILINE)
                clean_json = re.sub(r'^```\s*', '', clean_json, flags=re.MULTILINE).strip()

                if "STATUS: COMPLEX" not in clean_json.upper():
                    yield {"type": "result", "content": clean_json}
                    return
                else:
                    yield {"type": "result", "content": "STATUS: COMPLEX"}
                    return

        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            yield {"type": "debug", "content": f"TRACEBACK:\n{tb_str}"}
            yield {"type": "warning", "message": f"Local model offline or timed out. Falling back to Cloud APIs."}
            logger.warning(f"Ollama local routing failed or timed out: {e}. Falling back to flash-lite.")

        system_instruction_flash = (
            "You are an intent classifier for an Ableton DAW assistant. Classify the user's prompt into one of two categories. "
            "If the prompt is a simple, direct, single-step command (e.g., 'play', 'stop', 'create a track', 'set tempo to 120', 'delete clip'), return exactly the word 'FLASH'. "
            "If the prompt is ambiguous, requires creative reasoning, involves multiple complex steps, or asks a general question (e.g., 'make a techno beat', 'why is my track silent?', 'analyze this clip'), return exactly the word 'PRO'. "
            "Do not output any markdown, punctuation, or conversational text. Output only a single word."
        )
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction_flash,
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.flash_model,
                contents=prompt,
                config=config
            )
            result = response.text.strip().upper() if response.text else "PRO"
            if result == "FLASH":
                yield {"type": "result", "content": "STATUS: FLASH"}
                return
        except Exception as e:
            logger.error(f"Flash routing failed: {e}")

        yield {"type": "result", "content": "STATUS: COMPLEX"}

    async def chat(self, user_prompt: str, chat_history: list = None):
        """Executes an agentic multi-turn chat loop as an async generator."""
        if chat_history is None:
            chat_history = []
            
        route_result = ""
        async for chunk in self._route_intent(user_prompt):
            if chunk["type"] == "debug":
                yield json.dumps(chunk) + "\n"
                await asyncio.sleep(0.01)
            elif chunk["type"] == "result":
                route_result = chunk["content"]
                
        route_result_upper = route_result.upper()
        
        if "STATUS: COMPLEX" in route_result_upper:
            selected_model = self.pro_model
        elif "STATUS: FLASH" in route_result_upper:
            selected_model = self.flash_model
        else:
            try:
                # Sanitize markdown just in case before loading
                clean_json_str = route_result.strip()
                clean_json_str = re.sub(r'^```json\s*', '', clean_json_str, flags=re.MULTILINE)
                clean_json_str = re.sub(r'^```\s*', '', clean_json_str, flags=re.MULTILINE).strip()
                
                parsed = json.loads(clean_json_str)
                tool_name = parsed.get("tool")
                payload = parsed.get("payload", {})
                if tool_name in ["set_tempo", "start_playback", "stop_playback"] and hasattr(self, tool_name):
                    yield json.dumps({"type": "status", "message": "Local Model executing fast path..."}) + "\n"
                    await asyncio.sleep(0.01)
                    
                    method = getattr(self, tool_name)
                    payload.pop("dummy", None)
                    res = await asyncio.to_thread(method, **payload)
                    
                    yield json.dumps({
                        "type": "final",
                        "data": {
                            "response": f"Executed local fast path: {tool_name}\nResult: {res}",
                            "model_used": "gemma4:26b (Local)",
                            "input_tokens": 0,
                            "output_tokens": 0
                        }
                    }) + "\n"
                    return
                else:
                    yield json.dumps({"type": "warning", "message": f"Local model referenced an unknown tool: {tool_name}. Relying on Gemni Flash."}) + "\n"
                    selected_model = self.flash_model
            except json.JSONDecodeError:
                yield json.dumps({"type": "warning", "message": f"Failed to parse fast path JSON from local model. Falling back to Cloud."}) + "\n"
                logger.warning(f"Failed to parse fast path JSON from local model. Output was: {route_result.strip()}")
                selected_model = self.flash_model
            except Exception as e:
                yield json.dumps({"type": "warning", "message": f"Local fast path execution failed ({e}). Falling back to Cloud."}) + "\n"
                logger.warning(f"Error executing local fast path: {e}")
                selected_model = self.flash_model
        
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=self.tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
        
        contents = []
        for msg in chat_history:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            
            # Map UI roles to genai roles
            if role.lower() in ["assistant", "ai"]:
                role = "model"
            elif role.lower() != "model":
                role = "user"
                
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
            
        # Append the current prompt
        contents.append(
             types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
        )
        
        total_input_tokens = 0
        total_output_tokens = 0
        
        yield json.dumps({"type": "status", "message": "Agent thinking..."}) + "\n"
        await asyncio.sleep(0.01)
        
        response = await self.client.aio.models.generate_content(
            model=selected_model,
            contents=contents,
            config=config
        )
        
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            total_input_tokens += getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            total_output_tokens += getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            
        while response.function_calls:
            contents.append(response.candidates[0].content)
            tool_parts = []
            
            for fc in response.function_calls:
                func_name = fc.name
                args = fc.args if fc.args else {}
                
                yield json.dumps({"type": "status", "message": f"Agent calling: {func_name}..."}) + "\n"
                await asyncio.sleep(0.01)
                
                tool_result = None
                if hasattr(self, func_name):
                    method = getattr(self, func_name)
                    try:
                        res = await asyncio.to_thread(method, **args)
                        tool_result = {"result": res}
                    except TypeError as e:
                        if "positional argument" in str(e) or "missing" in str(e).lower():
                            tool_result = {"error": f"Missing required parameter. {str(e)}. You must use the appropriate 'get' tools (e.g., get_session_info, get_device_parameters) on the hierarchy first to find the correct index."}
                        else:
                            tool_result = {"error": str(e)}
                    except Exception as e:
                        tool_result = {"error": str(e)}
                else:
                    tool_result = {"error": f"Unknown tool: {func_name}"}
                    
                tool_parts.append(types.Part.from_function_response(name=func_name, response=tool_result))
                
            contents.append(types.Content(role="user", parts=tool_parts))
            
            yield json.dumps({"type": "status", "message": "Agent analyzing tool results..."}) + "\n"
            await asyncio.sleep(0.01)
            
            response = await self.client.aio.models.generate_content(
                model=selected_model,
                contents=contents,
                config=config
            )
            
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                total_input_tokens += getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                total_output_tokens += getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                
        final_text = response.text if response.text else "Tasks executed successfully."
                
        yield json.dumps({
            "type": "final",
            "data": {
                "response": final_text,
                "model_used": "PRO",
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens
            }
        }) + "\n"
        await asyncio.sleep(0.01)
