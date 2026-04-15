import os
import json
import logging
import asyncio
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
            "CRITICAL RULE: You MUST prioritize Compound Tools (like get_session_mix_status) over atomic tools to gather bulk data. "
            "Do not iterate through individual tracks to check states if a single bulk tool exists."
        )
        
        self.pro_model = "models/gemini-3.1-pro-preview-customtools"
        self.flash_model = "models/gemini-3.1-flash-lite-preview"
        
        # Tools to expose to the LLM
        self.tools = [
            self.test_ableton_connection,
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
            self.get_session_mix_status
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
        """Adds MIDI notes to a clip."""
        try:
            # Reconstruct the list as pydantic validation requires dict unpacking or straight execution
            valid_notes = [schema.NoteSchema(**n) if isinstance(n, dict) else n for n in notes]
            req = schema.AddNotesRequest(track_index=track_index, clip_slot_index=clip_slot_index, notes=valid_notes)
            return str(self._execute_proxy_request("add_notes_to_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)

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
        """Gets browser items available at a specific path, e.g. 'Instruments/Wavetable'."""
        try:
            req = schema.BrowserPathRequest(path=path)
            return str(self._execute_proxy_request("get_browser_items_at_path", **req.model_dump()))
        except ValidationError as e:
            return str(e)

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
        """[COMPOUND TOOL - PREFERRED] Creates a clip, names it, and populates it with MIDI notes in one step."""
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

    async def _route_intent(self, prompt: str) -> str:
        """Determines if the prompt is simple (FLASH) or complex (PRO)."""
        system_instruction = (
            "You are an intent classifier for an Ableton DAW assistant. Classify the user's prompt into one of two categories. "
            "If the prompt is a simple, direct, single-step command (e.g., 'play', 'stop', 'create a track', 'set tempo to 120', 'delete clip'), return exactly the word 'FLASH'. "
            "If the prompt is ambiguous, requires creative reasoning, involves multiple complex steps, or asks a general question (e.g., 'make a techno beat', 'why is my track silent?', 'analyze this clip'), return exactly the word 'PRO'. "
            "Do not output any markdown, punctuation, or conversational text. Output only a single word."
        )
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
        
        response = await self.client.aio.models.generate_content(
            model=self.flash_model,
            contents=prompt,
            config=config
        )
        
        result = response.text.strip().upper() if response.text else "PRO"
        if result != "FLASH":
            return "PRO"
        return "FLASH"

    async def chat(self, user_prompt: str, chat_history: list = None):
        """Executes an agentic multi-turn chat loop as an async generator."""
        if chat_history is None:
            chat_history = []
            
        model_to_use = await self._route_intent(user_prompt)
        selected_model = self.flash_model if model_to_use == "FLASH" else self.pro_model
        
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
                "model_used": "FLASH" if model_to_use == "FLASH" else "PRO",
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens
            }
        }) + "\n"
        await asyncio.sleep(0.01)
