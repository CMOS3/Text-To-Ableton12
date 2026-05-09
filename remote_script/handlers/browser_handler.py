import socket
from typing import Dict, Any, Tuple, Optional

class BrowserMixin:
    """Provides methods to traverse the Ableton Browser and load devices or resources."""

    def _do_get_browser_tree(self, client: socket.socket) -> None:
        """Retrieves the root-level folder structure of the Ableton Browser."""
        try:
            tree = []
            browser = self.application().browser
            for root_id in (
                "sounds",
                "drums",
                "instruments",
                "audio_effects",
                "midi_effects",
                "plugins",
                "packs",
            ):
                node = getattr(browser, root_id, None)
                if node:
                    tree.append({"name": node.name, "is_folder": node.is_folder})
            self._send_response(client, tree, apply_toon=False)
        except Exception as e:
            self._send_error(client, f"Get browser tree err: {e}")

    def _do_get_browser_items_at_path(self, args: Tuple[Dict[str, Any], socket.socket]) -> None:
        """Navigates to a specific browser path and retrieves its children items."""
        params, client = args
        try:
            path = str(params.get("path", ""))
            node = self._traverse_browser_path(path)
            if not node:
                self._send_error(client, f"Path '{path}' not found in Ableton Browser.")
                return

            items = []
            for child in node.children:
                items.append({"name": child.name, "is_folder": child.is_folder})

            self._send_response(client, items, apply_toon=False)
        except Exception as e:
            self._send_error(client, f"Get browser items err: {e}")

    def _traverse_browser_path(self, path: str) -> Optional[Any]:
        """Helper to walk the Ableton Browser tree given a string path (e.g., 'Instruments/Analog')."""
        parts = [p.strip() for p in path.split("/") if p.strip()]
        if not parts:
            return None

        browser = self.application().browser

        root_map = {
            "Sounds": browser.sounds,
            "Drums": browser.drums,
            "Instruments": browser.instruments,
            "Audio Effects": browser.audio_effects,
            "MIDI Effects": browser.midi_effects,
            "Max for Live": getattr(browser, "max_for_live", None),
            "Plug-ins": browser.plugins,
            "Packs": browser.packs,
            "User Library": browser.user_library,
        }

        current_node = root_map.get(parts[0])
        if not current_node:
            return None

        for i in range(1, len(parts)):
            part = parts[i]
            found = False
            for child in current_node.children:
                if child.name == part:
                    current_node = child
                    found = True
                    break
            if not found:
                return None

        return current_node

    def _do_load_device(self, args: Tuple[Dict[str, Any], socket.socket]) -> None:
        """Loads an instrument or effect from the browser onto a specific track."""
        params, client = args
        try:
            t_idx = int(params.get("track_index", 0))
            path = str(params.get("browser_path", ""))

            node = self._traverse_browser_path(path)
            if not node:
                self._send_error(
                    client, f"Device '{path}' not found in Ableton Browser."
                )
                return

            track = self.song().tracks[t_idx]
            self.song().view.selected_track = track
            self.application().browser.load_item(node)
            self.log_message(f"Loaded {path} onto track {t_idx}")
            self._send_response(client, "ok")
        except Exception as e:
            self.log_message(f"Load device err: {e}")
            self._send_error(client, f"Load device err: {e}")

    def _do_load_drum_kit(self, args: Tuple[Dict[str, Any], socket.socket]) -> None:
        """Loads a drum kit from the browser onto a specific track."""
        params, client = args
        try:
            t_idx = int(params.get("track_index", 0))
            path = str(params.get("drum_kit_path", ""))

            node = self._traverse_browser_path(path)
            if not node:
                self._send_error(
                    client, f"Drum Kit '{path}' not found in Ableton Browser."
                )
                return

            self.song().view.selected_track = self.song().tracks[t_idx]
            self.application().browser.load_item(node)
            self.log_message(f"Loaded drum kit {path} onto track {t_idx}")
            self._send_response(client, "ok")
        except Exception as e:
            self.log_message(f"Load drum kit err: {e}")
            self._send_error(client, f"Load drum kit err: {e}")

    def _do_fetch_resource(self, args: Tuple[Dict[str, Any], socket.socket]) -> None:
        """Fetches dynamic properties using deep URI routing for JIT retrieval."""
        params, client = args
        try:
            uri = str(params.get("uri", ""))
            data: Any = {}

            if uri.startswith("ableton://session/state"):
                tracks = [
                    {"i": i, "n": t.name, "dev": [str(d.name) for d in getattr(t, "devices", [])]} 
                    for i, t in enumerate(self.song().tracks)
                ]
                returns = [
                    {"i": i, "n": t.name, "dev": [str(d.name) for d in getattr(t, "devices", [])]}
                    for i, t in enumerate(self.song().return_tracks)
                ]
                try:
                    master_name = self.song().master_track.name
                    master_devs = [str(d.name) for d in getattr(self.song().master_track, "devices", [])]
                except Exception:
                    master_name = "Master"
                    master_devs = []

                scale_active = getattr(self.song(), "scale_mode", 0) == 1
                root_note = getattr(self.song(), "root_note", -1)
                scale_name = getattr(self.song(), "scale_name", "Unknown")

                data = {
                    "bpm": self.song().tempo,
                    "trk": tracks,
                    "returns": returns,
                    "master": {"n": master_name, "dev": master_devs},
                    "scale_active": scale_active,
                    "root_note": root_note,
                    "scale_name": scale_name,
                }
            elif uri.startswith("ableton://tracks/"):
                parts = uri.split("/")
                if len(parts) >= 5 and parts[4] == "state":
                    t_idx = int(parts[3])
                    if t_idx < len(self.song().tracks):
                        t = self.song().tracks[t_idx]
                        vol, pan = 0, 0
                        try:
                            vol = t.mixer_device.volume.value
                            pan = t.mixer_device.panning.value
                        except Exception:
                            pass
                        data = {"i": t_idx, "n": t.name, "v": vol, "p": pan}
                elif len(parts) >= 5 and parts[4] == "clip_slots":
                    t_idx = int(parts[3])
                    if t_idx < len(self.song().tracks):
                        t = self.song().tracks[t_idx]
                        slots = [
                            {
                                "s": j,
                                "has_clip": slot.has_clip,
                                "n": slot.clip.name
                                if slot.has_clip and slot.clip
                                else "",
                            }
                            for j, slot in enumerate(t.clip_slots)
                        ]
                        data = slots
                elif len(parts) >= 5 and parts[4] == "clips":
                    t_idx = int(parts[3])
                    if t_idx < len(self.song().tracks):
                        t = self.song().tracks[t_idx]
                        if len(parts) >= 7 and parts[6] == "notes":
                            c_idx = int(parts[5])
                            if c_idx < len(t.clip_slots):
                                clip = t.clip_slots[c_idx].clip
                                if clip:
                                    notes = clip.get_notes_extended(
                                        int(0), int(128), float(0.0), float(9999.0)
                                    )
                                    data = [
                                        {
                                            "pitch": n.pitch,
                                            "start_time": n.start_time,
                                            "duration": n.duration,
                                            "velocity": n.velocity,
                                        }
                                        for n in notes
                                    ]
                        else:
                            clips = [
                                {"s": j, "n": slot.clip.name}
                                for j, slot in enumerate(t.clip_slots)
                                if slot.has_clip and slot.clip
                            ]
                            data = clips
                elif len(parts) >= 5 and parts[4] == "devices":
                    t_idx = int(parts[3])
                    if t_idx < len(self.song().tracks):
                        t = self.song().tracks[t_idx]
                        devs = []
                        for j, d in enumerate(t.devices):
                            params_arr = [{"n": p.name, "v": p.value} for p in d.parameters]
                            devs.append({"i": j, "n": d.name, "p": params_arr})
                        data = devs
            self._send_response(client, {"uri": uri, "data": data})
        except Exception as e:
            self.log_message(f"Fetch resource err: {str(e)}")
            self._send_error(client, f"Fetch resource err: {str(e)}")
