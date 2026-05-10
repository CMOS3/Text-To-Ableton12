import re
import ast
import json
from typing import Any, Dict, List, Optional

from pydantic import ValidationError
from backend import schema
from backend.mcp_proxy import proxy
from backend.exceptions import AbletonProxyError, SchemaValidationError, ResourceNotFoundError
from backend.logger import get_json_logger

logger = get_json_logger(__name__)

class AbletonToolMixin:
    """Provides all the Ableton interaction tools for the CreativePlannerAgent."""

    def _execute_proxy_request(self, command: str, **kwargs: Any) -> Any:
        """
        Executes a proxy request to the Ableton Remote Script.
        
        Args:
            command: The method name to execute.
            **kwargs: Arguments to pass to the method.
            
        Returns:
            The parsed result from the proxy.
            
        Raises:
            AbletonProxyError: If the proxy fails or returns an error status.
        """
        try:
            res = proxy.request_state(command, kwargs)
        except Exception as e:
            logger.error("Failed to connect to Ableton Proxy", extra={"extra_data": {"command": command, "error": str(e)}})
            raise AbletonProxyError(f"Connection failed: {str(e)}") from e

        if not isinstance(res, dict):
            logger.error("Invalid proxy response format", extra={"extra_data": {"command": command, "response": res}})
            raise AbletonProxyError("Received non-dictionary response from proxy.")

        if res.get("status") != "success":
            msg = res.get("message", "Unknown failure")
            logger.error("Proxy returned failure status", extra={"extra_data": {"command": command, "message": msg}})
            raise AbletonProxyError(f"Ableton Proxy Error: {res.get('status')} - {msg}")

        data = res.get("data", {})
        if isinstance(data, dict) and "error" in data:
            logger.error("Ableton returned an error", extra={"extra_data": {"command": command, "error": data["error"]}})
            raise AbletonProxyError(f"Ableton Error: {data['error']}")

        if isinstance(data, dict) and "result" in data:
            return data["result"]

        return data

    def fetch_resource(self, uri: str) -> str:
        """Fetches a specific DAW resource (like track state, session, clips) for Just-In-Time context."""
        try:
            req = schema.FetchResourceRequest(uri=uri)
            return str(self._execute_proxy_request("fetch_resource", **req.model_dump()))
        except ValidationError as e:
            logger.warning("Validation error in fetch_resource", extra={"extra_data": {"uri": uri, "error": str(e)}})
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def test_ableton_connection(self) -> str:
        """Attempts to send a JSON 'ping' message to the Ableton Server."""
        try:
            res = self._execute_proxy_request("ping")
            return str(res)
        except AbletonProxyError as e:
            return str(e)

    def get_song_scale(self) -> str:
        """Retrieves whether Scale Mode is active, the root note, and the scale name (e.g. Minor, Major)."""
        try:
            return str(self._execute_proxy_request("get_song_scale"))
        except AbletonProxyError as e:
            return str(e)

    def get_session_info(self) -> str:
        """Retrieves the current tracks and state in the Ableton Live session."""
        try:
            res = self._execute_proxy_request("get_session_info")
            return str(res)
        except AbletonProxyError as e:
            return str(e)

    def set_tempo(self, tempo: float) -> str:
        """Sets the tempo (BPM) of the Ableton session."""
        try:
            req = schema.TempoRequest(tempo=tempo)
            return str(self._execute_proxy_request("set_tempo", **req.model_dump()))
        except ValidationError as e:
            return f"Validation error: {e}"
        except AbletonProxyError as e:
            return str(e)

    def start_playback(self) -> str:
        """Starts playback in Ableton."""
        try:
            return str(self._execute_proxy_request("start_playback"))
        except AbletonProxyError as e:
            return str(e)

    def stop_playback(self) -> str:
        """Stops playback in Ableton."""
        try:
            return str(self._execute_proxy_request("stop_playback"))
        except AbletonProxyError as e:
            return str(e)

    def get_track_info(self, track_index: int) -> str:
        """Gets detailed info about a specific track by its integer index (0-indexed)."""
        try:
            req = schema.GetTrackInfoRequest(track_index=track_index)
            return str(self._execute_proxy_request("get_track_info", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def create_midi_track(self, track_name: str) -> str:
        """Creates a new MIDI track in Ableton Live."""
        try:
            req = schema.TrackNameRequest(track_name=track_name)
            return str(self._execute_proxy_request("create_midi_track", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def set_track_name(self, track_index: int, name: str) -> str:
        """Sets the name of a specific track."""
        try:
            req = schema.TrackIndexNameRequest(track_index=track_index, name=name)
            return str(self._execute_proxy_request("set_track_name", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def select_track(self, track_name: str) -> str:
        """Selects (focuses) a track by name."""
        try:
            return str(self._execute_proxy_request("select_track", **{"track_name": track_name}))
        except AbletonProxyError as e:
            return str(e)

    def arm_track(self, track_name: str, arm: bool = True) -> str:
        """Arms or disarms a track for recording by name."""
        try:
            return str(
                self._execute_proxy_request("arm_track", **{"track_name": track_name, "arm": arm})
            )
        except AbletonProxyError as e:
            return str(e)

    def create_clip(
        self, track_index: int, clip_slot_index: int, length: float, clip_name: str = ""
    ) -> str:
        """Creates a new MIDI clip in a specific track and clip slot."""
        try:
            req = schema.CreateClipRequest(
                track_index=track_index,
                clip_slot_index=clip_slot_index,
                length=length,
                clip_name=clip_name,
            )
            return str(self._execute_proxy_request("create_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def set_clip_name(self, track_index: int, clip_slot_index: int, name: str) -> str:
        """Sets the name of an existing clip."""
        try:
            req = schema.SetClipNameRequest(
                track_index=track_index, clip_slot_index=clip_slot_index, name=name
            )
            return str(self._execute_proxy_request("set_clip_name", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def add_notes_to_clip(
        self, track_index: int, clip_slot_index: int, notes: List[schema.NoteSchema]
    ) -> str:
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
            req = schema.AddNotesRequest(
                track_index=track_index, clip_slot_index=clip_slot_index, notes=valid_notes
            )
            return str(self._execute_proxy_request("add_notes_to_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except Exception as e:
            logger.error("Failed to add notes to clip", extra={"extra_data": {"error": str(e)}})
            return f"Error adding notes: {e}"

    def fire_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Fires (plays) a specific clip."""
        try:
            return str(
                self._execute_proxy_request(
                    "fire_clip", **{"track_index": track_index, "clip_slot_index": clip_slot_index}
                )
            )
        except AbletonProxyError as e:
            return str(e)

    def stop_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Stops playback of a specific clip."""
        try:
            return str(
                self._execute_proxy_request(
                    "stop_clip", **{"track_index": track_index, "clip_slot_index": clip_slot_index}
                )
            )
        except AbletonProxyError as e:
            return str(e)

    def get_browser_tree(self) -> str:
        """Retrieves the root level tree of the Ableton Live browser."""
        try:
            return str(self._execute_proxy_request("get_browser_tree"))
        except AbletonProxyError as e:
            return str(e)

    def get_browser_items_at_path(self, path: str) -> str:
        """Retrieves a list of children items and folders at a specific path in the Ableton Live browser. Use this to dive deeper into folders."""
        try:
            req = schema.BrowserItemsRequest(path=path)
            return str(self._execute_proxy_request("get_browser_items_at_path", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def _pitch_name_to_midi(self, pitch_name: str) -> int:
        """Converts a pitch name (e.g., 'C1', 'F#2', 'Bb-1') to a MIDI note number (0-127)."""
        if not pitch_name:
            raise SchemaValidationError("Empty pitch name provided")

        match = re.match(r"^([a-gA-G])([#b])?(-?[0-9]+)$", pitch_name.strip())
        if not match:
            raise SchemaValidationError(f"Invalid pitch name format: {pitch_name}")

        note_str, accidental, octave_str = match.groups()
        octave = int(octave_str)

        note_map = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
        base_pitch = note_map[note_str.lower()]

        if accidental == "#":
            base_pitch += 1
        elif accidental == "b":
            base_pitch -= 1

        midi_note = (octave + 2) * 12 + base_pitch

        if midi_note < 0 or midi_note > 127:
            raise SchemaValidationError(f"MIDI note out of range (0-127) for {pitch_name}: {midi_note}")

        return midi_note

    def inject_midi_to_new_clip(
        self, track_index: int, length: float, notes: List[Any], clip_name: str = ""
    ) -> str:
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
                    logger.warning("Skipping invalid note", extra={"extra_data": {"pitch_name": pitch_name, "error": str(ve)}})

            if not processed_notes:
                return "Failed to parse any valid MIDI notes."

            req = schema.InjectMidiRequest(
                track_index=track_index, length=length, clip_name=clip_name, notes=processed_notes
            )

            return str(self._execute_proxy_request("inject_midi_to_new_clip", **req.model_dump()))
        except Exception as e:
            logger.error("Error injecting midi", extra={"extra_data": {"error": str(e)}})
            return f"Error injecting midi: {e}"

    def load_instrument_or_effect(self, track_index: int, browser_path: str) -> str:
        """Loads a device (instrument or effect) onto a track from the browser."""
        try:
            req = schema.LoadDeviceRequest(track_index=track_index, browser_path=browser_path)
            return str(self._execute_proxy_request("load_instrument_or_effect", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def load_preset_rack(self, track_index: int, rack_name: str) -> str:
        """Loads a custom .adg preset rack from the Text-to-Ableton user library folder."""
        try:
            browser_path = f"User Library/Presets/Text-to-Ableton/{rack_name}.adg"
            return self.load_instrument_or_effect(track_index, browser_path)
        except Exception as e:
            return str(e)

    def load_drum_kit(self, track_index: int, drum_kit_path: str) -> str:
        """Loads a drum kit onto a track."""
        try:
            req = schema.LoadDrumKitRequest(track_index=track_index, drum_kit_path=drum_kit_path)
            return str(self._execute_proxy_request("load_drum_kit", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def get_notes_from_clip(self, track_index: int, clip_slot_index: int) -> str:
        """Retrieves an array of all notes in a specific clip."""
        try:
            req = schema.GetNotesFromClipRequest(
                track_index=track_index, clip_slot_index=clip_slot_index
            )
            return str(self._execute_proxy_request("get_notes_from_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def delete_notes_from_clip(
        self, track_index: int, clip_slot_index: int, notes: List[schema.NoteSchema]
    ) -> str:
        """Deletes specific notes from a clip based on precisely matching both pitch and start_time."""
        try:
            valid_notes = [schema.NoteSchema(**n) if isinstance(n, dict) else n for n in notes]
            req = schema.DeleteNotesRequest(
                track_index=track_index, clip_slot_index=clip_slot_index, notes=valid_notes
            )
            return str(self._execute_proxy_request("delete_notes_from_clip", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def get_track_devices(self, track_index: int) -> str:
        """Gets all devices loaded on a specific track."""
        try:
            req = schema.GetTrackDevicesRequest(track_index=track_index)
            return str(self._execute_proxy_request("get_track_devices", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def get_device_parameters(self, track_index: int, device_index: int) -> str:
        """Gets all parameters for a device on a track to discover their names, minimums, and maximums."""
        try:
            req = schema.DeviceIndexRequest(track_index=track_index, device_index=device_index)
            return str(self._execute_proxy_request("get_device_parameters", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def set_device_parameter(
        self, track_index: int, device_index: int, parameter_name: str, value: float
    ) -> str:
        """Sets the numeric value of a specific parameter by its string name on a device."""
        try:
            req = schema.SetDeviceParameterByNameRequest(
                track_index=track_index,
                device_index=device_index,
                parameter_name=parameter_name,
                value=value,
            )
            return str(self._execute_proxy_request("set_device_parameter", **req.model_dump()))
        except ValidationError as e:
            return str(e)
        except AbletonProxyError as e:
            return str(e)

    def mix_track(
        self, track_index: int, volume: Optional[float] = None, panning: Optional[float] = None, mute: Optional[bool] = None
    ) -> str:
        """Sets mixer properties (volume, panning, mute) for a track."""
        try:
            params: Dict[str, Any] = {"track_index": track_index}
            if volume is not None:
                params["volume"] = volume
            if panning is not None:
                params["panning"] = panning
            if mute is not None:
                params["mute"] = mute
            return str(self._execute_proxy_request("set_track_mixer", **params))
        except AbletonProxyError as e:
            return str(e)
        except Exception as e:
            return str(e)

    def get_session_mix_status(self) -> str:
        """Retrieves a summary of volume/gain status for all tracks in the session in one go."""
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
        except AbletonProxyError as e:
            return str(e)
        except Exception as e:
            return str(e)

    def set_device_parameter_batch(
        self, track_index: int, device_index: int, parameters: List[Any]
    ) -> str:
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
                    "value": tweak.get("value"),
                }
                self._execute_proxy_request("set_device_parameter", **payload)
                success_keys.append(f"{payload['parameter_name']} ({payload['value']})")

            return "Successfully updated parameters:\n" + "\n".join(f"- {s}" for s in success_keys)

        except AbletonProxyError as e:
            return str(e)
        except Exception as e:
            logger.error("Batch parameter set failed", extra={"extra_data": {"error": str(e)}})
            return f"Error executing set_device_parameter_batch: {str(e)}"

    def _flatten_schema(self, node: Any, defs: Dict[str, Any]) -> Any:
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

    def _generate_minified_schemas(self) -> List[Dict[str, Any]]:
        """Generates minified JSON schemas for the exposed tools to feed into the prompt."""
        tool_schema_map = {
            "fetch_resource": schema.FetchResourceRequest,
            "create_midi_track": schema.TrackNameRequest,
            "set_track_name": schema.TrackIndexNameRequest,
            "set_clip_name": schema.SetClipNameRequest,
            "load_preset_rack": schema.LoadPresetRackRequest,
            "load_instrument_or_effect": schema.LoadDeviceRequest,
            "load_drum_kit": schema.LoadDrumKitRequest,
            "mix_track": schema.MixTrackRequest,
            "inject_midi_to_new_clip": schema.InjectMidiRequest,
            "set_device_parameter_batch": schema.SetDeviceParameterBatchRequest,
            "search_device_parameters": schema.SearchDeviceParametersRequest,
        }

        tool_list = []
        for func in getattr(self, "tools", []): # self.tools is defined in CreativePlannerAgent
            func_name = func.__name__
            description = func.__doc__ or ""

            tool_def: Dict[str, Any] = {"name": func_name, "description": description, "args": {}}

            if func_name in tool_schema_map and tool_schema_map[func_name]:
                js_schema = tool_schema_map[func_name].model_json_schema()  # type: ignore
                defs = js_schema.get("$defs", {})
                flattened = self._flatten_schema(js_schema, defs)

                tool_def["args"] = flattened.get("properties", {})
                if "required" in flattened:
                    tool_def["required"] = flattened["required"]

            tool_list.append(tool_def)

        tool_list.append(
            {
                "name": "ui_text_response",
                "description": "Used to return text, advice, or sound design tips directly to the user.",
                "args": {
                    "text": {
                        "type": "string",
                        "description": "The textual response or advice to show the user.",
                    }
                },
                "required": ["text"],
            }
        )

        return tool_list
