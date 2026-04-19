import ast
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
            "You are a local Ableton session orchestrator with access to a full suite of Ableton Live tools. "
            "You can control transport, tracks, clips, and the browser. "
            "You must use 0-based indexing for tracks and devices. "
            "For `add_notes_to_clip`, make sure to pass a structured list of properties. "
            "When asked to create a clip or generate notes, you MUST call `get_song_scale` first to establish the `root_note` and `scale_name`. Use this as your musical foundation. "
            "CRITICAL RULE: You MUST prioritize Compound Tools (like get_session_mix_status) over atomic tools to gather bulk data. "
            "Do not iterate through individual tracks to check states if a single bulk tool exists. "
            "CRITICAL TIME RULE: Ableton length and time values are strictly in BEATS, not bars! "
            "If the user asks for a 4-bar loop in 4/4 time, you MUST set length to 16.0. 1 Bar = 4.0 Beats. "
            "CRITICAL: If you call `consult_cloud_expert`, DO NOT attempt to execute the sound design steps it returns. Simply synthesize the text and present the guide to the user, then stop."
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
            self.get_track_devices,
            self.get_device_parameters,
            self.set_device_parameter,
            self.set_track_volume_by_name,
            self.load_device_to_track_by_name,
            self.generate_named_midi_pattern,
            self.get_session_mix_status,
            self.inject_midi_to_new_clip,
            self.consult_cloud_expert
        ]
        
        self.atomic_tools = [
            self.set_tempo,
            self.start_playback,
            self.stop_playback
        ]
        
        self._cloud_consult_telemetry = {"p_tokens": 0, "c_tokens": 0, "used": False}

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

    def get_track_devices(self, track_index: int) -> str:
        """Gets all devices loaded on a specific track. Args: track_index (int): The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc."""
        try:
            req = schema.TrackDevicesRequest(track_index=track_index)
            return str(self._execute_proxy_request("get_track_devices", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def get_device_parameters(self, track_index: int, device_index: int) -> str:
        """Gets all parameters for a device on a track to discover their names, minimums, and maximums. You MUST use this before set_device_parameter. WARNING: Many Ableton parameters (Hz, dB, ms) are normalized to floats between 0.0 and 1.0. You must inspect the `min` and `max` values returned by this tool. Args: track_index (int): The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc."""
        try:
            req = schema.DeviceIndexRequest(track_index=track_index, device_index=device_index)
            return str(self._execute_proxy_request("get_device_parameters", **req.model_dump()))
        except ValidationError as e:
            return str(e)

    def set_device_parameter(self, track_index: int, device_index: int, parameter_name: str, value: float) -> str:
        """Sets the numeric value of a specific parameter by its string name on a device. CRITICAL: If the parameter's min is 0.0 and max is 1.0, the value is normalized. You CANNOT send absolute real-world values (e.g., 400 for 400Hz). You MUST mathematically estimate and scale the desired real-world value into a float between 0.0 and 1.0 before making this call."""
        try:
            req = schema.SetDeviceParameterByNameRequest(track_index=track_index, device_index=device_index, parameter_name=parameter_name, value=value)
            return str(self._execute_proxy_request("set_device_parameter", **req.model_dump()))
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

    async def consult_cloud_expert(self, query: str) -> str:
        """[COMPOUND TOOL - PREFERRED] Consults an advanced cloud AI expert for advice on Ableton Live, music production, or sound design. Use this when you are unsure how to achieve a sound or use a feature. Do not use this tool for requesting parameter changes; this expert provides text advice only."""
        print(f"DEBUG: consult_cloud_expert triggered with query='{query}'")
        try:
            sys_instruct = (
                "You are an expert Ableton Live and sound design consultant. Provide clear, concise, "
                "step-by-step advice to help the user achieve their musical goals. Avoid formatting "
                "with markdown code blocks for JSON, just return plain text readable advice."
            )
            
            config = types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=0.7,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
            
            response = await self.client.aio.models.generate_content(
                model=self.pro_model,
                contents=query,
                config=config
            )
            
            if response.usage_metadata:
                p_toks = getattr(response.usage_metadata, "prompt_token_count", 0)
                c_toks = getattr(response.usage_metadata, "candidates_token_count", 0)
                self._cloud_consult_telemetry = {"p_tokens": p_toks, "c_tokens": c_toks, "used": True}
                
            return response.text if response.text else "The expert did not return any advice."
        except Exception as e:
            return f"Error querying cloud expert: {e}"

    # --- Chat Engine ---

    async def _generate_ollama_tools(self) -> list[dict]:
        tool_schema_map = {
            "test_ableton_connection": None,
            "get_song_scale": None,
            "get_session_info": None,
            "set_tempo": schema.TempoRequest,
            "start_playback": None,
            "stop_playback": None,
            "get_track_info": schema.TrackIndexRequest,
            "create_midi_track": schema.TrackNameRequest,
            "set_track_name": schema.TrackIndexNameRequest,
            "select_track": schema.TrackNameRequest,
            "arm_track": schema.TrackArmRequest,
            "create_clip": schema.CreateClipRequest,
            "set_clip_name": schema.SetClipNameRequest,
            "add_notes_to_clip": schema.AddNotesRequest,
            "fire_clip": schema.ClipActionRequest,
            "stop_clip": schema.ClipActionRequest,
            "get_browser_tree": None,
            "get_browser_items_at_path": schema.BrowserItemsRequest,
            "load_instrument_or_effect": schema.LoadDeviceRequest,
            "load_drum_kit": schema.LoadDrumKitRequest,
            "get_notes_from_clip": schema.ClipActionRequest,
            "delete_notes_from_clip": schema.DeleteNotesRequest,
            "delete_track": schema.TrackIndexRequest,
            "delete_clip": schema.ClipActionRequest,
            "get_track_devices": schema.TrackDevicesRequest,
            "get_device_parameters": schema.DeviceIndexRequest,
            "set_device_parameter": schema.SetDeviceParameterByNameRequest,
            "set_track_volume_by_name": schema.SetTrackVolumeByNameRequest,
            "load_device_to_track_by_name": schema.LoadDeviceToTrackByNameRequest,
            "generate_named_midi_pattern": schema.GenerateNamedMidiPatternRequest,
            "get_session_mix_status": None,
            "inject_midi_to_new_clip": schema.InjectMidiRequest,
            "consult_cloud_expert": schema.ConsultCloudExpertRequest
        }
        
        ollama_tools = []
        for func in self.tools:
            func_name = func.__name__
            description = func.__doc__ or ""
            
            parameters = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            if func_name in tool_schema_map and tool_schema_map[func_name]:
                js_schema = tool_schema_map[func_name].model_json_schema()
                parameters["properties"] = js_schema.get("properties", {})
                if "required" in js_schema:
                    parameters["required"] = js_schema["required"]
                    
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": description,
                    "parameters": parameters
                }
            })
        return ollama_tools

    async def chat(self, user_prompt: str, chat_history: list = None):
        """Executes an agentic multi-turn chat loop via native Ollama tool calling."""
        if chat_history is None:
            chat_history = []
            
        loop_count = 0
        MAX_ITERATIONS = 5
        total_prompt_tokens = 0
        total_candidate_tokens = 0
        models_used_chain = ["VladimirGav/gemma4-26b-16GB-VRAM (Local Orchestrator)"]
        
        messages = [{"role": "system", "content": self.system_instruction}]
        
        for msg in chat_history:
            role = "assistant" if msg.get("role", "").lower() in ["assistant", "ai", "model"] else "user"
            messages.append({"role": role, "content": msg.get("content", "")})
            
        messages.append({"role": "user", "content": user_prompt})
        
        tools_payload = await self._generate_ollama_tools()
        
        yield json.dumps({"type": "status", "message": "Agent thinking..."}) + "\n"
        await asyncio.sleep(0.01)
        
        while True:
            loop_count += 1
            if loop_count > MAX_ITERATIONS:
                yield json.dumps({
                    "type": "final",
                    "data": {
                        "response": "Execution halted to protect memory (too many iterations).",
                        "model_used": "\n".join(models_used_chain),
                        "input_tokens": total_prompt_tokens,
                        "output_tokens": total_candidate_tokens
                    }
                }) + "\n"
                break
                
            payload = {
                "model": "VladimirGav/gemma4-26b-16GB-VRAM",
                "messages": messages,
                "tools": tools_payload,
                "stream": False,
                "options": {
                    "num_ctx": 4096,
                    "temperature": 0.0
                },
                "keep_alive": -1
            }
            
            with open("ollama_debug_log.txt", "a", encoding="utf-8") as log_file:
                log_file.write(f"\n{'='*50}\nRAW PAYLOAD SENT TO OLLAMA:\n{json.dumps(payload, indent=2)}\n{'='*50}\n")

            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    res = await client.post("http://127.0.0.1:11434/api/chat", json=payload)
                    res.raise_for_status()
                    data = res.json()
                    
                    with open("ollama_debug_log.txt", "a", encoding="utf-8") as log_file:
                        log_file.write(f"\n{'*'*50}\nRAW RESPONSE RECEIVED FROM OLLAMA:\n{json.dumps(data.get('message', {}), indent=2)}\n{'*'*50}\n")
            except Exception as e:
                import traceback
                tb_str = traceback.format_exc()
                
                print("\n" + "!"*50)
                print("BACKEND CRASH TRACE:")
                print(tb_str)
                print("!"*50 + "\n")

                yield json.dumps({"type": "debug", "content": f"OLLAMA_ERROR:\n{tb_str}"}) + "\n"
                yield json.dumps({
                    "type": "final",
                    "data": {
                        "response": f"System error communicating with Ollama: {e}",
                        "model_used": "\n".join(models_used_chain),
                        "input_tokens": total_prompt_tokens,
                        "output_tokens": total_candidate_tokens
                    }
                }) + "\n"
                break
                
            response_message = data.get("message", {})
            
            total_prompt_tokens += data.get("prompt_eval_count", 0)
            total_candidate_tokens += data.get("eval_count", 0)
            
            messages.append(response_message)
            
            tool_calls = response_message.get("tool_calls")
            if tool_calls:
                yield json.dumps({"type": "status", "message": "Executing tools..."}) + "\n"
                await asyncio.sleep(0.01)
                
                for tc in tool_calls:
                    func_name = tc.get("function", {}).get("name")
                    args = tc.get("function", {}).get("arguments", {})
                    
                    yield json.dumps({"type": "status", "message": f"Agent calling: {func_name}..."}) + "\n"
                    await asyncio.sleep(0.01)
                    
                    tool_result = None
                    is_cloud_expert = (func_name == "consult_cloud_expert")
                    
                    if hasattr(self, func_name):
                        method = getattr(self, func_name)
                        try:
                            if asyncio.iscoroutinefunction(method):
                                res = await method(**args)
                            else:
                                res = await asyncio.to_thread(method, **args)
                                
                            # --- CLEAN DIRTY STRINGIFIED DICTS ---
                            if isinstance(res, str) and res.strip().startswith("{") and "'" in res:
                                try:
                                    res = ast.literal_eval(res)
                                except Exception:
                                    pass
                            # -------------------------------------
                                    
                            tool_result = {"result": res}
                        except TypeError as e:
                            if "positional argument" in str(e) or "missing" in str(e).lower():
                                tool_result = {"error": f"Missing required parameter. {str(e)}."}
                            else:
                                tool_result = {"error": str(e)}
                        except Exception as e:
                            tool_result = {"error": str(e)}
                    else:
                        tool_result = {"error": f"Unknown tool: {func_name}"}
                        
                    # Aggregate Cloud Telemetry
                    if getattr(self, "_cloud_consult_telemetry", {}).get("used"):
                        total_prompt_tokens += self._cloud_consult_telemetry.get("p_tokens", 0)
                        total_candidate_tokens += self._cloud_consult_telemetry.get("c_tokens", 0)
                        if "Gemini 3.1 Pro (Cloud Expert Consultation)" not in models_used_chain:
                            models_used_chain.append("Gemini 3.1 Pro (Cloud Expert Consultation)")
                        self._cloud_consult_telemetry = {"p_tokens": 0, "c_tokens": 0, "used": False}
                        
                    # --- THE STRUCTURAL BYPASS ---
                    if is_cloud_expert:
                        # Extract the string result from the tool
                        cloud_text = tool_result.get("result", "No advice returned.") if isinstance(tool_result, dict) else str(tool_result)
                        
                        # Yield directly to UI, skipping the local model entirely
                        yield json.dumps({
                            "type": "final",
                            "data": {
                                "response": str(cloud_text),
                                "model_used": "\n".join(models_used_chain),
                                "input_tokens": total_prompt_tokens,
                                "output_tokens": total_candidate_tokens
                            }
                        }) + "\n"
                        
                        # Hard stop the generator. This physically kills the while loop.
                        return 
                    # -----------------------------
                    else:
                        result_str = json.dumps(tool_result, default=str)
                        messages.append({
                            "role": "tool",
                            "name": func_name,
                            "content": result_str
                        })
                        
                yield json.dumps({"type": "status", "message": "Agent analyzing tool results..."}) + "\n"
                await asyncio.sleep(0.01)
            else:
                final_text = response_message.get("content", "")
                if not final_text:
                    final_text = "Tasks executed successfully."
                    
                yield json.dumps({
                    "type": "final",
                    "data": {
                        "response": final_text,
                        "model_used": "\n".join(models_used_chain),
                        "input_tokens": total_prompt_tokens,
                        "output_tokens": total_candidate_tokens
                    }
                }) + "\n"
                break
