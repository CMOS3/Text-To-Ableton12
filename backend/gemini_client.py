import ast
import os
import json
import logging
import asyncio
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

from .mcp_proxy import proxy
from . import schema

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
class RetrieverAgent:
    def __init__(self, api_key: str = None):
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment.")
        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-3.1-flash-lite-preview"
        self.prompt_tokens = 0
        self.candidate_tokens = 0

    async def execute_task(self, task_description: str, context_data: str, response_schema: type, max_retries: int = 2):
        """
        Executes a localized task using Flash-Lite, enforcing Structured Outputs and 
        utilizing a self-correction loop for validation errors.
        """
        prompt = f"TASK:\n{task_description}\n\nCONTEXT:\n{context_data}\n\nIMPORTANT: You must output ONLY a valid JSON object matching the requested schema. No markdown wrapping."
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=response_schema
        )
        
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                    config=config
                )
                
                if response.usage_metadata:
                    self.prompt_tokens += getattr(response.usage_metadata, "prompt_token_count", 0)
                    self.candidate_tokens += getattr(response.usage_metadata, "candidates_token_count", 0)
                
                if not response.text:
                    raise ValueError("Empty response from model.")
                    
                data = json.loads(response.text)
                validated_obj = response_schema(**data)
                return validated_obj
                
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                if attempt == max_retries:
                    raise Exception(f"RetrieverAgent failed to produce valid JSON after {max_retries} retries. Error: {str(e)}")
                
                # JSON Patch Refinement: Feed the exact error back to the model
                error_msg = str(e)
                prompt += f"\n\nERROR ON PREVIOUS ATTEMPT:\nThe parser threw this error:\n{error_msg}\n\nPlease analyze the error and output a corrected JSON payload that strictly matches the schema."

    async def search_catalog(self, device_name: str, intent: str) -> str:
        """Searches the local device_catalog.json for parameters matching the intent."""
        catalog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "device_catalog.json")
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        except Exception as e:
            return f"Error loading catalog: {e}"
            
        # Case insensitive key matching since Planner might pass 'wavetable' instead of 'Wavetable'
        target_key = None
        for k in catalog.keys():
            if k.lower() == device_name.lower():
                target_key = k
                break
                
        if not target_key:
            return f"Device '{device_name}' not found in the ground-truth catalog. (Available: {', '.join(catalog.keys())})"
            
        device_params = catalog[target_key].get("parameters", [])
        
        task_description = f"The Planner wants to achieve this intent: '{intent}' on the device '{device_name}'. Find all relevant parameters."
        context_data = json.dumps(device_params)
        
        try:
            response = await self.execute_task(
                task_description=task_description,
                context_data=context_data,
                response_schema=schema.RetrieverSearchResponse,
                max_retries=2
            )
            return response.model_dump_json()
        except Exception as e:
            return f"Retriever search failed: {e}"

    async def generate_session_title(self, first_prompt: str) -> str:
        """Generates a short, concise title (max 4 words) for a session based on the first prompt."""
        task_description = "Generate a concise title (maximum 4 words) for a music production session based on the user's first prompt. Respond ONLY with the title string, no quotes."
        context_data = first_prompt
        
        prompt = f"TASK:\n{task_description}\n\nUSER PROMPT:\n{context_data}"
        
        config = types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="text/plain"
        )
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                config=config
            )
            title = response.text.strip().replace('"', '')
            return title if title else "Untitled Session"
        except Exception as e:
            logger.error(f"Failed to generate session title: {e}")
            return "Untitled Session"

class CreativePlannerAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        print(f"DEBUG: GEMINI_API_KEY found: {bool(api_key)}")
        
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment. Please ensure you have a '.env' file "
                "in the project root directory with 'GEMINI_API_KEY=your_key_here'."
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
            self.set_track_volume_by_name,
            self.mix_track,
            self.inject_midi_to_new_clip,
            self.set_device_parameter_batch,
            self.search_device_parameters
        ]
        
        self.atomic_tools = []
        
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
            "You have access to a suite of Ableton proxy tools to control the session.\n"
            "You MUST output exactly ONE valid JSON array containing a sequential script of actions.\n"
            "Example format:\n"
            "[\n"
            "   {\"tool\": \"create_midi_track\", \"args\": {\"track_name\": \"Drums\"}},\n"
            "   {\"tool\": \"ui_text_response\", \"args\": {\"text\": \"I have created your Drums track.\"}}\n"
            "]\n"
            "CRITICAL: If you create a new track, you must calculate its new `track_index` for subsequent tools. The new index is ALWAYS equal to the current total number of tracks in the session (e.g., if the provided session state shows 4 existing tracks [indexes 0,1,2,3], the newly created track will be index 4).\n"
            "CRITICAL: DO NOT HALLUCINATE TOOL NAMES. You must ONLY use the exact tool names provided in the minified JSON schemas below. Do not invent tools like 'load_device_to_track_by_name'. If a tool requires a `track_index`, you MUST use the integer index.\n"
            "If the user asks for advice, sound design guidance, or plain text communication, you MUST use the synthetic tool `ui_text_response` and provide the text in its `text` argument. Use Markdown within this text.\n"
            "DO NOT wrap your JSON in markdown code blocks. NO backticks. Output valid JSON array only.\n"
            "Here are the available target tools mapped as minified JSON:\n"
            + json.dumps(self._generate_minified_schemas(), separators=(',', ':'))
        )

    # --- Core Toolset Implementations ---

    def _execute_proxy_request(self, command: str, **kwargs):
        res = proxy.request_state(command, kwargs if kwargs else None)
        
        if res.get("status") != "success":
            raise Exception(f"Ableton Proxy Error: {res.get('status')} - {res.get('message', '')}")
            
        data = res.get("data", {})
        if isinstance(data, dict) and "error" in data:
            raise Exception(f"Ableton Error: {data['error']}")
            
        if isinstance(data, dict) and "result" in data:
            return data["result"]
            
        return data


    def fetch_resource(self, uri: str) -> str:
        """Fetches a specific DAW resource (like track state, session, clips) for Just-In-Time context."""
        try:
            req = schema.FetchResourceRequest(uri=uri)
            return str(self._execute_proxy_request("fetch_resource", **req.model_dump()))
        except ValidationError as e:
            return str(e)

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
        try:
            req = schema.GetTrackInfoRequest(track_index=track_index)
            return str(self._execute_proxy_request("get_track_info", **req.model_dump()))
        except ValidationError as e:
            return str(e)

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
        return str(self._execute_proxy_request("arm_track", **{"track_name": track_name, "arm": arm}))

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
        return str(self._execute_proxy_request("fire_clip", **{"track_index": track_index, "clip_slot_index": clip_slot_index}))

    def stop_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Stops playback of a specific clip."""
        return str(self._execute_proxy_request("stop_clip", **{"track_index": track_index, "clip_slot_index": clip_slot_index}))

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

    def _pitch_name_to_midi(self, pitch_name: str) -> int:
        """Converts a pitch name (e.g., 'C1', 'F#2', 'Bb-1') to a MIDI note number (0-127)."""
        import re
        if not pitch_name:
            raise ValueError("Empty pitch name")
            
        match = re.match(r"^([a-gA-G])([#b])?(-?[0-9]+)$", pitch_name.strip())
        if not match:
            raise ValueError(f"Invalid pitch name format: {pitch_name}")
            
        note_str, accidental, octave_str = match.groups()
        octave = int(octave_str)
        
        note_map = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
        base_pitch = note_map[note_str.lower()]
        
        if accidental == '#':
            base_pitch += 1
        elif accidental == 'b':
            base_pitch -= 1
            
        midi_note = (octave + 2) * 12 + base_pitch
        
        if midi_note < 0 or midi_note > 127:
            raise ValueError(f"MIDI note out of range (0-127) for {pitch_name}: {midi_note}")
            
        return midi_note

    def inject_midi_to_new_clip(self, track_index: int, length: float, notes: list) -> str:
        """Finds the first empty clip slot on the track, creates a clip of the specified length, and injects notes."""
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
                    continue
                
                try:
                    midi_val = self._pitch_name_to_midi(pitch_name)
                    note_dict["pitch"] = midi_val
                    processed_notes.append(schema.SemanticNoteSchema(**note_dict))
                except Exception as ve:
                    print(f"Skipping invalid note {pitch_name}: {ve}")
                    
            if not processed_notes:
                return "Failed to parse any valid MIDI notes."
                
            req = schema.InjectMidiRequest(track_index=track_index, length=length, notes=processed_notes)
            
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
            req = schema.GetNotesFromClipRequest(track_index=track_index, clip_slot_index=clip_slot_index)
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
        return str(self._execute_proxy_request("delete_track", **{"track_index": track_index}))

    def delete_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Deletes a clip from a specific track and slot index."""
        return str(self._execute_proxy_request("delete_clip", **{"track_index": track_index, "clip_slot_index": clip_slot_index}))

    def get_track_devices(self, track_index: int) -> str:
        """Gets all devices loaded on a specific track. Args: track_index (int): The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc."""
        try:
            req = schema.GetTrackDevicesRequest(track_index=track_index)
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

    def mix_track(self, track_index: int, volume: float = None, panning: float = None, mute: bool = None) -> str:
        """[COMPOUND TOOL - PREFERRED] Sets mixer properties (volume, panning, mute) for a track."""
        try:
            params = {"track_index": track_index}
            if volume is not None:
                params["volume"] = volume
            if panning is not None:
                params["panning"] = panning
            if mute is not None:
                params["mute"] = mute
            return str(self._execute_proxy_request("set_track_mixer", **params))
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
    async def search_device_parameters(self, device_name: str, intent: str) -> str:
        """[RAG TOOL] Semantically searches for parameter names and value bounds for a specific device based on your musical intent."""
        return await self.retriever.search_catalog(device_name, intent)

    def set_device_parameter_batch(self, track_index: int, device_index: int, parameters: list) -> str:
        """Sets multiple parameters on a single device sequentially."""
        try:
            success_keys = []
            for p in parameters:
                if hasattr(p, "model_dump"):
                    tweak = p.model_dump()
                elif isinstance(p, dict):
                    tweak = p
                else:
                    tweak = getattr(p, "__dict__", {})
                    
                payload = {
                    "track_index": track_index,
                    "device_index": device_index,
                    "parameter_name": tweak.get("parameter_name"),
                    "value": tweak.get("value")
                }
                self._execute_proxy_request("set_device_parameter", **payload)
                success_keys.append(f"{payload['parameter_name']} ({payload['value']})")
                
            return f"Successfully updated parameters:\n" + "\n".join(f"- {s}" for s in success_keys)
            
        except Exception as e:
            return f"Error executing set_device_parameter_batch: {str(e)}"

    # --- Chat Engine ---

    def _flatten_schema(self, node, defs: dict):
        """Recursively flattens JSON schemas by resolving $ref pointers and stripping $defs."""
        if isinstance(node, list):
            return [self._flatten_schema(item, defs) for item in node]
        elif isinstance(node, dict):
            new_node = {}
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    ref_key = v.split("/")[-1]
                    if ref_key in defs:
                        resolved = self._flatten_schema(defs[ref_key], defs)
                        new_node.update(resolved)
                elif k == "$defs":
                    continue
                else:
                    new_node[k] = self._flatten_schema(v, defs)
            return new_node
        else:
            return node

    def _generate_minified_schemas(self) -> list:
        tool_schema_map = {
            "fetch_resource": schema.FetchResourceRequest,
            "create_midi_track": schema.TrackNameRequest,
            "set_track_name": schema.TrackIndexNameRequest,
            "set_clip_name": schema.SetClipNameRequest,
            "load_instrument_or_effect": schema.LoadDeviceRequest,
            "set_track_volume_by_name": schema.SetTrackVolumeByNameRequest,
            "mix_track": schema.MixTrackRequest,
            "inject_midi_to_new_clip": schema.InjectMidiRequest,
            "set_device_parameter_batch": schema.SetDeviceParameterBatchRequest,
            "search_device_parameters": schema.SearchDeviceParametersRequest
        }
        
        tool_list = []
        for func in self.tools:
            func_name = func.__name__
            description = func.__doc__ or ""
            
            tool_def = {
                "name": func_name,
                "description": description,
                "args": {}
            }
            
            if func_name in tool_schema_map and tool_schema_map[func_name]:
                js_schema = tool_schema_map[func_name].model_json_schema()
                defs = js_schema.get("$defs", {})
                flattened = self._flatten_schema(js_schema, defs)
                
                tool_def["args"] = flattened.get("properties", {})
                if "required" in flattened:
                    tool_def["required"] = flattened["required"]
                    
            tool_list.append(tool_def)
            
        tool_list.append({
            "name": "ui_text_response",
            "description": "Used to return text, advice, or sound design tips directly to the user.",
            "args": {
                "text": {
                    "type": "string",
                    "description": "The textual response or advice to show the user."
                }
            },
            "required": ["text"]
        })
            
        return tool_list

    async def chat(self, user_prompt: str, chat_history: list = None, require_approval: bool = True):
        """Executes a Single-Shot Compiler agent to fulfill the prompt."""
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
            role = "model" if msg.get("role", "").lower() in ["assistant", "ai", "model"] else "user"
            content_text = msg.get("content", "")
            
            # Prevent double injection: if the last message is from the user,
            # we merge it into the final augmented prompt instead of appending it as a separate turn.
            if i == history_len - 1 and role == "user":
                if content_text:
                    final_user_text = content_text
                continue
                
            if content_text:
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content_text)]))
            
        yield json.dumps({"type": "status", "message": "Pre-fetching session state locally..."}) + "\n"
        await asyncio.sleep(0.01)
        
        try:
            session_state = await asyncio.to_thread(self.fetch_resource, "ableton://session/state")
        except Exception as e:
            session_state = f"Failed to pre-fetch session: {e}"
            
        augmented_prompt = f"LOCAL SESSION STATE:\n{session_state}\n\nUSER PROMPT:\n{final_user_text}\n\nNOTE: If you need more track details to execute the intent, output ONLY `fetch_resource` actions first. The system will run them and return the results so you can decide the final actions."
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=augmented_prompt)]))
        
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=0.0,
            response_mime_type="application/json",
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
        
        yield json.dumps({"type": "status", "message": "Supervisor analyzing..."}) + "\n"
        await asyncio.sleep(0.01)
        
        turn_count = 0
        max_turns = 4
        
        while turn_count < max_turns:
            turn_count += 1
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.pro_model,
                    contents=contents,
                    config=config
                )
            except Exception as e:
                import traceback
                tb_str = traceback.format_exc()
                yield json.dumps({"type": "debug", "content": f"GEMINI_API_ERROR:\n{tb_str}"}) + "\n"
                yield json.dumps({
                    "type": "final",
                    "data": {
                        "response": f"System error communicating with Gemini API: {e}",
                        "model_used": "\n".join(models_used_chain),
                        "input_tokens": total_prompt_tokens,
                        "output_tokens": total_candidate_tokens
                    }
                }) + "\n"
                return
            
            if response.usage_metadata:
                total_prompt_tokens += getattr(response.usage_metadata, "prompt_token_count", 0)
                total_candidate_tokens += getattr(response.usage_metadata, "candidates_token_count", 0)
            
            if not response.text:
                yield json.dumps({
                    "type": "final",
                    "data": {
                        "response": "Error: Empty response from model.",
                        "model_used": "\n".join(models_used_chain),
                        "input_tokens": total_prompt_tokens,
                        "output_tokens": total_candidate_tokens
                    }
                }) + "\n"
                return
            
            print("\n--- RAW LLM PAYLOAD ---")
            print(response.text)
            
            raw_text = response.text.strip()
            start_idx = raw_text.find('[')
        
            clean_text = raw_text
            if start_idx != -1:
                # Safely find the matching closing bracket by parsing characters
                in_string = False
                escape = False
                depth = 0
                end_idx = -1
            
                for i in range(start_idx, len(raw_text)):
                    char = raw_text[i]
                    if escape:
                        escape = False
                    elif char == '\\':
                        escape = True
                    elif char == '"':
                        in_string = not in_string
                    elif not in_string:
                        if char == '[':
                            depth += 1
                        elif char == ']':
                            depth -= 1
                            if depth == 0:
                                end_idx = i
                                break
                            
                if end_idx != -1:
                    clean_text = raw_text[start_idx:end_idx + 1]
                else:
                    fallback_end = raw_text.rfind(']')
                    if fallback_end >= start_idx:
                        clean_text = raw_text[start_idx:fallback_end + 1]
            
                try:
                    script_actions = json.loads(clean_text)
                    if not isinstance(script_actions, list):
                        script_actions = [script_actions]
                except json.JSONDecodeError as e:
                    yield json.dumps({
                        "type": "final",
                        "data": {
                            "response": f"Error decoding model JSON output: {e}\nRaw output: {response.text}",
                            "model_used": "\n".join(models_used_chain),
                            "input_tokens": total_prompt_tokens,
                            "output_tokens": total_candidate_tokens
                        }
                    }) + "\n"
                    return
                
                # ReAct Loop Check: Are there only context-gathering actions?
                has_mutations = any(a.get("tool") not in ["fetch_resource", "ui_text_response", "search_device_parameters"] for a in script_actions)
                has_fetches = any(a.get("tool") in ["fetch_resource", "search_device_parameters"] for a in script_actions)
            
                if not has_mutations and has_fetches:
                    fetch_results = []
                    for action in script_actions:
                        if action.get("tool") == "fetch_resource":
                            uri = action.get("args", {}).get("uri", "")
                            if uri:
                                yield json.dumps({"type": "status", "message": f"Supervisor fetching {uri}..."}) + "\n"
                                res = await asyncio.to_thread(self.fetch_resource, uri)
                                fetch_results.append(f"Result for {uri}:\n{res}")
                        elif action.get("tool") == "search_device_parameters":
                            d_name = action.get("args", {}).get("device_name", "")
                            intent = action.get("args", {}).get("intent", "")
                            yield json.dumps({"type": "status", "message": f"RAG Search: {d_name} -> '{intent}'..."}) + "\n"
                            res = await self.search_device_parameters(d_name, intent)
                            fetch_results.append(f"Result for RAG search '{d_name}':\n{res}")
                            
                    # Append the model's action and the tool results to the history
                    contents.append(response.candidates[0].content)
                    contents.append(types.Content(role="user", parts=[types.Part.from_text(text="\n\n".join(fetch_results))]))
                    continue # Loop again to get the next action from the model
                
                # If we reach here, there are mutations or no fetches, so we break the ReAct loop
                break
            
            # End of ReAct loop
        
        if require_approval:
            yield json.dumps({"type": "approval_required", "actions": script_actions}) + "\n"
            await self.approval_event.wait()
            
            if not getattr(self, "is_approved", False):
                yield json.dumps({
                    "type": "final",
                    "data": {
                        "response": "Execution cancelled by user.",
                        "model_used": "\n".join(models_used_chain),
                        "input_tokens": total_prompt_tokens,
                        "output_tokens": total_candidate_tokens
                    }
                }) + "\n"
                return
            
        yield json.dumps({"type": "status", "message": f"Executing {len(script_actions)} actions locally..."}) + "\n"
        await asyncio.sleep(0.01)
        
        responses_accumulated = []
        for i, action in enumerate(script_actions):
            tool_name = action.get("tool")
            args = action.get("args", {})
            
            if not tool_name:
                continue
                
            yield json.dumps({"type": "status", "message": f"Executing {i+1}/{len(script_actions)}: {tool_name}..."}) + "\n"
            await asyncio.sleep(0.01)
            
            if tool_name == "ui_text_response":
                text_content = args.get("text", "")
                responses_accumulated.append(text_content)
                continue
                
            if hasattr(self, tool_name):
                method = getattr(self, tool_name)
                try:
                    if asyncio.iscoroutinefunction(method):
                        res = await method(**args)
                    else:
                        res = await asyncio.to_thread(method, **args)
                        
                    if tool_name == "get_device_parameters":
                        with open("parameter_dump.txt", "w") as f:
                            f.write(str(res))
                    
                    if isinstance(res, str) and res.strip().startswith("{") and "'" in res:
                        try:
                            res = ast.literal_eval(res)
                        except Exception:
                            pass
                            
                    if tool_name in ["set_device_parameter_batch", "inject_midi_to_new_clip"]:
                        yield json.dumps({"type": "status", "message": f"Action Result:\n{res}"}) + "\n"
                    
                    await asyncio.sleep(0.5)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    yield json.dumps({"type": "status", "message": f"Error in {tool_name}: {e}"}) + "\n"
            else:
                error_msg = f"Hallucinated Tool Error: The LLM attempted to call a non-existent tool '{tool_name}'."
                print(f"\n[ERROR] {error_msg}")
                yield json.dumps({"type": "status", "message": error_msg}) + "\n"
                
        final_text = "\n\n".join(responses_accumulated) if responses_accumulated else "Tasks executed successfully."
        
        yield json.dumps({
            "type": "final",
            "data": {
                "response": final_text,
                "model_used": "PRO_AND_FLASH",
                "pro_input_tokens": total_prompt_tokens,
                "pro_output_tokens": total_candidate_tokens,
                "flash_input_tokens": self.retriever.prompt_tokens,
                "flash_output_tokens": self.retriever.candidate_tokens
            }
        }) + "\n"
