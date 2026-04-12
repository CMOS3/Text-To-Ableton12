import os
import json
import logging
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
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        self.client = genai.Client(api_key=api_key)
        
        self.system_instruction = (
            "You are a session-aware Ableton expert. You have access to a full suite of Ableton Live tools. "
            "You can control transport, tracks, clips, and the browser. "
            "Always try to gather context (like session info or browser trees) before making destructive or complex actions, "
            "unless the user is explicitly specific. For `add_notes_to_clip`, make sure to pass a structured list of properties. "
        )
        
        self.model_name = "models/gemini-3.1-pro-preview-customtools"
        
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
            self.set_device_parameters
        ]

    # --- Core Toolset Implementations ---

    def test_ableton_connection(self) -> str:
        """Attempts to send a JSON 'ping' message to the Ableton Server."""
        res = proxy.ping()
        return str(res)

    def get_session_info(self) -> str:
        """Retrieves the current tracks and state in the Ableton Live session."""
        res = proxy.request_state("get_session_info")
        return str(res)

    def set_tempo(self, tempo: float) -> str:
        """Sets the tempo (BPM) of the Ableton session."""
        try:
            req = schema.TempoRequest(tempo=tempo)
            return str(proxy.send_command("set_tempo", req.model_dump()))
        except ValidationError as e:
            return f"Validation error: {e}"

    def start_playback(self) -> str:
        """Starts playback in Ableton."""
        return str(proxy.send_command("start_playback"))

    def stop_playback(self) -> str:
        """Stops playback in Ableton."""
        return str(proxy.send_command("stop_playback"))

    def get_track_info(self, track_index: int) -> str:
        """Gets detailed info about a specific track by its integer index (0-indexed)."""
        return str(proxy.request_state("get_track_info", {"track_index": track_index}))

    def create_midi_track(self, track_name: str) -> str:
        """Creates a new MIDI track in Ableton Live."""
        try:
            req = schema.TrackNameRequest(track_name=track_name)
            return str(proxy.send_command("create_midi_track", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def set_track_name(self, track_index: int, name: str) -> str:
        """Sets the name of a specific track."""
        try:
            req = schema.TrackIndexNameRequest(track_index=track_index, name=name)
            return str(proxy.send_command("set_track_name", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def select_track(self, track_name: str) -> str:
        """Selects (focuses) a track by name."""
        return str(proxy.send_command("select_track", {"track_name": track_name}))

    def arm_track(self, track_name: str, arm: bool = True) -> str:
        """Arms or disarms a track for recording by name."""
        try:
            req = schema.TrackArmRequest(track_name=track_name, arm=arm)
            return str(proxy.send_command("arm_track", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def create_clip(self, track_index: int, clip_slot_index: int, length: float) -> str:
        """Creates a new MIDI clip in a specific track and clip slot."""
        try:
            req = schema.CreateClipRequest(track_index=track_index, clip_slot_index=clip_slot_index, length=length)
            return str(proxy.send_command("create_clip", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def set_clip_name(self, track_index: int, clip_slot_index: int, name: str) -> str:
        """Sets the name of an existing clip."""
        try:
            req = schema.SetClipNameRequest(track_index=track_index, clip_slot_index=clip_slot_index, name=name)
            return str(proxy.send_command("set_clip_name", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def add_notes_to_clip(self, track_index: int, clip_slot_index: int, notes: list[schema.NoteSchema]) -> str:
        """Adds MIDI notes to a clip."""
        try:
            # Reconstruct the list as pydantic validation requires dict unpacking or straight execution
            valid_notes = [schema.NoteSchema(**n) if isinstance(n, dict) else n for n in notes]
            req = schema.AddNotesRequest(track_index=track_index, clip_slot_index=clip_slot_index, notes=valid_notes)
            return str(proxy.send_command("add_notes_to_clip", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def fire_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Fires (plays) a specific clip."""
        try:
            req = schema.ClipActionRequest(track_index=track_index, clip_slot_index=clip_slot_index)
            return str(proxy.send_command("fire_clip", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def stop_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Stops playback of a specific clip."""
        try:
            req = schema.ClipActionRequest(track_index=track_index, clip_slot_index=clip_slot_index)
            return str(proxy.send_command("stop_clip", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def get_browser_tree(self) -> str:
        """Retrieves the root level tree of the Ableton Live browser."""
        return str(proxy.request_state("get_browser_tree"))

    def get_browser_items_at_path(self, path: str) -> str:
        """Gets browser items available at a specific path, e.g. 'Instruments/Wavetable'."""
        try:
            req = schema.BrowserPathRequest(path=path)
            return str(proxy.request_state("get_browser_items_at_path", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def load_instrument_or_effect(self, track_index: int, browser_path: str) -> str:
        """Loads a device (instrument or effect) onto a track from the browser."""
        try:
            req = schema.LoadDeviceRequest(track_index=track_index, browser_path=browser_path)
            return str(proxy.send_command("load_instrument_or_effect", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def load_drum_kit(self, track_index: int, drum_kit_path: str) -> str:
        """Loads a drum kit onto a track."""
        try:
            req = schema.LoadDrumKitRequest(track_index=track_index, drum_kit_path=drum_kit_path)
            return str(proxy.send_command("load_drum_kit", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def get_notes_from_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Retrieves an array of all notes in a specific clip."""
        try:
            req = schema.ClipActionRequest(track_index=track_index, clip_slot_index=clip_slot_index)
            return str(proxy.request_state("get_notes_from_clip", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def delete_notes_from_clip(self, track_index: int, clip_slot_index: int, notes: list[schema.NoteSchema]) -> str:
        """Deletes specific notes from a clip based on precisely matching both pitch and start_time."""
        try:
            valid_notes = [schema.NoteSchema(**n) if isinstance(n, dict) else n for n in notes]
            req = schema.DeleteNotesRequest(track_index=track_index, clip_slot_index=clip_slot_index, notes=valid_notes)
            return str(proxy.send_command("delete_notes_from_clip", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def delete_track(self, track_index: int) -> str:
        """Deletes a track by its integer index."""
        try:
            req = schema.TrackIndexRequest(track_index=track_index)
            return str(proxy.send_command("delete_track", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def delete_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Deletes a clip from a specific track and slot index."""
        try:
            req = schema.ClipActionRequest(track_index=track_index, clip_slot_index=clip_slot_index)
            return str(proxy.send_command("delete_clip", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def get_device_parameters(self, track_index: int, device_index: int = 0) -> str:
        """Gets all parameters for a device on a track to discover their parameter_index. You MUST use this before set_device_parameters."""
        try:
            req = schema.DeviceIndexRequest(track_index=track_index, device_index=device_index)
            return str(proxy.request_state("get_device_parameters", req.model_dump()))
        except ValidationError as e:
            return str(e)

    def set_device_parameters(self, track_index: int, device_index: int, parameter_index: int, value: float) -> str:
        """Sets the numeric value of a specific parameter index on a device."""
        try:
            req = schema.SetDeviceParameterRequest(track_index=track_index, device_index=device_index, parameter_index=parameter_index, value=value)
            return str(proxy.send_command("set_device_parameters", req.model_dump()))
        except ValidationError as e:
            return str(e)

    # --- Chat Engine ---

    def chat(self, user_prompt: str) -> str:
        """Executes a single-turn chat with the Gemini model."""
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=self.tools,
        )
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config
        )
        
        result_texts = []
        if response.function_calls:
            for fc in response.function_calls:
                func_name = fc.name
                args = fc.args if fc.args else {}
                
                # Dynamically call the corresponding method matching the function name
                if hasattr(self, func_name):
                    method = getattr(self, func_name)
                    try:
                        # Attempt to pass args directly
                        tool_result = method(**args) 
                        result_texts.append(f"Model invoked tool '{func_name}'.\nResult: {tool_result}")
                    except Exception as e:
                        result_texts.append(f"Error executing '{func_name}': {str(e)}")
                else:
                    result_texts.append(f"Model attempted to call unknown tool: {func_name}")
                    
        if response.text:
            result_texts.append(response.text)
                
        return "\n".join(result_texts)
