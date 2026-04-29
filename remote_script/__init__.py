from _Framework.ControlSurface import ControlSurface
import socket
import threading
import json
import queue
import Live
import re
import hashlib

class GeminiRemoteScript(ControlSurface):
    def __init__(self, c_instance):
        super().__init__(c_instance)
        self.server = None
        self.task_queue = queue.Queue()
        self.mcp_thread = threading.Thread(target=self.start_mcp_listener, daemon=True)
        self.mcp_thread.start()

    def disconnect(self):
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
        super().disconnect()

    def start_mcp_listener(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind(('127.0.0.1', 9877))
            self.server.listen(5)
            self.log_message("Ableton MCP Listener started on 127.0.0.1:9877")
            
            while True:
                try:
                    client, addr = self.server.accept()
                    threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
                except Exception as e:
                    # accept will throw an error if self.server.close() is called
                    self.log_message(f"Accept error or stopped: {e}")
                    break
        except Exception as e:
            self.log_message(f"Could not bind to port 9877: {e}")

    def handle_client(self, client):
        try:
            while True:
                data = client.recv(65536)
                if not data:
                    break
                
                # Split by newline if client sends multiple commands together
                for line in data.decode('utf-8').strip().split('\n'):
                    if not line: continue
                    try:
                        payload = json.loads(line)
                        method = payload.get("method") or payload.get("type")
                        params = payload.get("params", {})
                        
                        self._dispatch_method(method, params, client)
                    except json.JSONDecodeError as e:
                        self.log_message(f"MCP JSON error: {e}")
        except Exception as e:
            self.log_message(f"MCP Connection error: {e}")
        finally:
            client.close()

    def _send_response(self, client, data):
        try:
            response = json.dumps({"result": data}) + "\n"
            client.sendall(response.encode('utf-8'))
        except Exception as e:
            self.log_message(f"Error sending response: {e}")

    def _send_error(self, client, error_msg):
        try:
            response = json.dumps({"error": error_msg}) + "\n"
            client.sendall(response.encode('utf-8'))
        except Exception:
            pass

    def update_display(self):
        super().update_display()
        try:
            while not self.task_queue.empty():
                task = self.task_queue.get_nowait()
                task()
        except Exception as e:
            self.log_message(f"Queue execution error: {e}")

    def execute_safely(self, func, *args):
        def task():
            try:
                func(*args)
            except Exception as e:
                self.log_message(f"Execute error in {func.__name__}: {e}")
        self.task_queue.put(task)

    def _dispatch_method(self, method, params, client):
        self.log_message(f"Dispatching method: {method} with params: {params}")
        if method == "ping":
            self.execute_safely(self._do_ping, client)
        elif method == "get_song_scale":
            self.schedule_message(1, self._do_get_song_scale, (client,))
        
        # --- Session & Transport ---
        elif method == "get_session_info":
            self.execute_safely(self._do_get_session_info, client)
        elif method == "get_track_list":  # Legacy fallback
            self.execute_safely(self._do_get_session_info, client)
        elif method == "set_tempo":
            self.execute_safely(self._do_set_tempo, params.get("tempo", 120.0))
            self._send_response(client, "ok")
        elif method == "start_playback":
            self.execute_safely(self._do_start_playback)
            self._send_response(client, "ok")
        elif method == "stop_playback":
            self.execute_safely(self._do_stop_playback)
            self._send_response(client, "ok")
            
        # --- Track Management ---
        elif method == "create_midi_track":
            track_name = params.get("track_name", "Gemini MIDI Track")
            self.execute_safely(self._do_create_midi_track, track_name)
            self._send_response(client, "ok")
        elif method == "set_track_name":
            self.execute_safely(self._do_set_track_name, (params.get("track_index", 0), params.get("name", "")))
            self._send_response(client, "ok")
        elif method == "select_track":
            self.execute_safely(self._do_select_track, params.get("track_name", ""))
            self._send_response(client, "ok")
        elif method == "arm_track":
            self.execute_safely(self._do_arm_track, (params.get("track_name", ""), params.get("arm", True)))
            self._send_response(client, "ok")
            
        # --- Clip Operations (Stubbed / Basic) ---
        elif method == "create_clip":
            self.execute_safely(self._do_create_clip, params)
            self._send_response(client, "ok")
        elif method == "set_clip_name":
            self.execute_safely(self._do_set_clip_name, params)
            self._send_response(client, "ok")
        elif method == "fire_clip":
            self.execute_safely(self._do_fire_clip, params)
            self._send_response(client, "ok")
        elif method == "stop_clip":
            self.execute_safely(self._do_stop_clip, params)
            self._send_response(client, "ok")
        elif method == "add_notes_to_clip":
            self.execute_safely(self._do_add_notes, params)
            self._send_response(client, "ok")
            
        # --- Browser Management ---
        elif method == "get_browser_tree":
            self.execute_safely(self._do_get_browser_tree, client)
        elif method == "get_browser_items_at_path":
            self.execute_safely(self._do_get_browser_items_at_path, (params, client))
        elif method == "inject_midi_to_new_clip":
            self.execute_safely(self._do_inject_midi_to_new_clip, (params, client))
        elif method == "load_instrument_or_effect":
            self.execute_safely(self._do_load_device, (params, client))
        elif method == "load_drum_kit":
            self.execute_safely(self._do_load_drum_kit, (params, client))
        elif method == "fetch_resource":
            self.execute_safely(self._do_fetch_resource, (params, client))
            
        # --- Advanced Editing & Parameters ---
        elif method == "get_notes_from_clip":
            self.execute_safely(self._do_get_notes_from_clip, (params, client))
        elif method == "delete_notes_from_clip":
            self.execute_safely(self._do_delete_notes_from_clip, params)
            self._send_response(client, "ok")
        elif method == "delete_track":
            self.execute_safely(self._do_delete_track, params)
            self._send_response(client, "ok")
        elif method == "delete_clip":
            self.execute_safely(self._do_delete_clip, params)
            self._send_response(client, "ok")
        elif method == "get_track_devices":
            self.execute_safely(self._do_get_track_devices, (params, client))
        elif method == "get_device_parameters":
            self.execute_safely(self._do_get_device_parameters, (params, client))
        elif method == "set_device_parameter":
            self.execute_safely(self._do_set_device_parameter, (params, client))
        elif method == "set_track_mixer":
            self.execute_safely(self._do_set_track_mixer, (params, client))
        else:
            self.log_message(f"MCP: Unknown method '{method}'")

    # ---- Handlers ----
    def _do_get_song_scale(self, args):
        client, = args
        try:
            is_active = getattr(self.song(), "scale_mode", 0) == 1
            root_note = getattr(self.song(), "root_note", -1)
            scale_name = getattr(self.song(), "scale_name", "Unknown")
            self._send_response(client, {
                "is_active": is_active,
                "root_note": root_note, 
                "scale_name": scale_name
            })
        except Exception as e:
            self._send_error(client, str(e))

    def _do_ping(self, client):
        self._send_response(client, "pong")

    def _generate_etag(self, data_str):
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()[:8]

    def _to_toon(self, obj):
        """Basic TOON (Token-Oriented Object Notation) compression"""
        if isinstance(obj, dict):
            return "{" + ",".join(f"{k}:{self._to_toon(v)}" for k, v in obj.items()) + "}"
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return "[" + ",".join(self._to_toon(v) for v in obj) + "]"
        elif isinstance(obj, str):
            if re.match(r'^[a-zA-Z0-9_]+$', obj): return obj
            escaped = obj.replace('"', '\\"')
            return f'"{escaped}"'
        elif isinstance(obj, bool):
            return "T" if obj else "F"
        elif obj is None:
            return "N"
        else:
            if isinstance(obj, float):
                return f"{obj:.3f}".rstrip('0').rstrip('.')
            return str(obj)

    def _do_fetch_resource(self, args):
        params, client = args
        try:
            uri = params.get("uri", "")
            data = {}
            
            if uri.startswith("ableton://session/state"):
                tracks = [{"i": i, "n": t.name} for i, t in enumerate(self.song().tracks)]
                data = {"bpm": self.song().tempo, "trk": tracks}
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
                        except: pass
                        data = {"i": t_idx, "n": t.name, "v": vol, "p": pan}
                elif len(parts) >= 5 and parts[4] == "clips":
                    t_idx = int(parts[3])
                    if t_idx < len(self.song().tracks):
                        t = self.song().tracks[t_idx]
                        clips = [{"s": j, "n": slot.clip.name} for j, slot in enumerate(t.clip_slots) if slot.has_clip and slot.clip]
                        data = clips
                elif len(parts) >= 5 and parts[4] == "devices":
                    t_idx = int(parts[3])
                    if t_idx < len(self.song().tracks):
                        t = self.song().tracks[t_idx]
                        devs = []
                        for j, d in enumerate(t.devices):
                            params = [{"n": p.name, "v": p.value} for p in d.parameters]
                            devs.append({"i": j, "n": d.name, "p": params})
                        data = devs
            
            toon_str = self._to_toon(data)
            etag = self._generate_etag(toon_str)
            
            self._send_response(client, {
                "uri": uri,
                "data": toon_str,
                "etag": etag
            })
        except Exception as e:
            self.log_message(f"Fetch resource err: {str(e)}")
            self._send_error(client, f"Fetch resource err: {str(e)}")

    def _do_get_session_info(self, client):
        try:
            tracks_info = []
            for i, track in enumerate(self.song().tracks):
                vol = "UNKNOWN"
                pan = "UNKNOWN"
                try:
                    vol = track.mixer_device.volume.value
                    pan = track.mixer_device.panning.value
                except Exception:
                    pass
                
                track_type = "midi" if getattr(track, "has_midi_input", False) else "audio"
                devices = [str(d.name) for d in getattr(track, "devices", [])]
                
                clips = {}
                try:
                    for j, slot in enumerate(track.clip_slots):
                        if slot.has_clip and getattr(slot, "clip", None):
                            clips[str(j)] = str(slot.clip.name)
                except Exception:
                    pass
                    
                tracks_info.append({
                    "index": i, 
                    "name": track.name, 
                    "type": track_type,
                    "volume": vol,
                    "panning": pan,
                    "devices": devices,
                    "clips": clips
                })
                
            returns_info = []
            for i, track in enumerate(self.song().return_tracks):
                vol = "UNKNOWN"
                pan = "UNKNOWN"
                try:
                    vol = track.mixer_device.volume.value
                    pan = track.mixer_device.panning.value
                except Exception:
                    pass
                    
                devices = [str(d.name) for d in getattr(track, "devices", [])]
                
                returns_info.append({
                    "index": i,
                    "name": track.name,
                    "volume": vol,
                    "panning": pan,
                    "devices": devices
                })
                
            master_info = {}
            try:
                master = self.song().master_track
                vol = "UNKNOWN"
                pan = "UNKNOWN"
                try:
                    vol = master.mixer_device.volume.value
                    pan = master.mixer_device.panning.value
                except Exception:
                    pass
                    
                devices = [str(d.name) for d in getattr(master, "devices", [])]
                
                master_info = {
                    "volume": vol,
                    "panning": pan,
                    "devices": devices
                }
            except Exception:
                pass
            
            info = {
                "tempo": self.song().tempo,
                "is_playing": self.song().is_playing,
                "root_note": getattr(self.song(), "root_note", -1),
                "scale_name": getattr(self.song(), "scale_name", "Unknown"),
                "tracks": tracks_info,
                "returns": returns_info,
                "master": master_info
            }
            self._send_response(client, info)
        except Exception as e:
            self._send_error(client, str(e))

    def _do_set_tempo(self, tempo):
        try:
            self.song().tempo = tempo
            self.log_message(f"Set tempo to {tempo}")
        except Exception as e:
            self.log_message(str(e))

    def _do_start_playback(self):
        self.song().is_playing = True

    def _do_stop_playback(self):
        self.song().is_playing = False

    def _do_create_midi_track(self, track_name):
        try:
            self.song().create_midi_track(-1)
            new_track = self.song().tracks[-1]
            new_track.name = track_name
            self.log_message(f"Created MIDI track: {track_name}")
        except Exception as e:
            self.log_message(f"Error creating track: {e}")

    def _do_set_track_name(self, args):
        idx, name = args
        try:
            self.song().tracks[idx].name = name
        except Exception as e:
            self.log_message(f"Error setting track name: {e}")

    def _do_select_track(self, track_name):
        for track in self.song().tracks:
            if track.name == track_name:
                self.song().view.selected_track = track
                return

    def _do_arm_track(self, args):
        track_name, arm = args
        for track in self.song().tracks:
            if track.name == track_name and track.can_be_armed:
                track.arm = arm

    def _do_create_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            length = params.get("length", 4.0)
            slot = self.song().tracks[t_idx].clip_slots[c_idx]
            if not slot.has_clip:
                slot.create_clip(length)
        except Exception as e:
            self.log_message(f"Create clip err: {e}")
            
    def _do_fire_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            self.song().tracks[t_idx].clip_slots[c_idx].fire()
        except Exception as e:
            self.log_message(f"Fire clip err: {e}")

    def _do_set_clip_name(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            name = params.get("name", "New Clip")
            clip = self.song().tracks[t_idx].clip_slots[c_idx].clip
            if clip:
                clip.name = name
        except Exception as e:
            self.log_message(f"Set clip name err: {e}")

    def _do_stop_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            self.song().tracks[t_idx].clip_slots[c_idx].stop()
        except Exception as e:
            self.log_message(f"Stop clip err: {e}")
            
    def _do_add_notes(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            notes_req = params.get("notes", [])
            
            clip = self.song().tracks[t_idx].clip_slots[c_idx].clip
            if not clip: return
            
            notes_to_add = tuple(Live.Clip.MidiNoteSpecification(
                pitch=n["pitch"],
                start_time=n["start_time"],
                duration=n["duration"],
                velocity=n["velocity"],
                mute=False
            ) for n in notes_req)
            clip.add_new_notes(notes_to_add)
        except Exception as e:
            self.log_message(f"Add notes err: {e}")

    # --- Browser Management Additions ---
    
    def _do_get_browser_tree(self, client):
        try:
            tree = []
            browser = self.application().browser
            for root_id in ('sounds', 'drums', 'instruments', 'audio_effects', 'midi_effects', 'plugins', 'packs'):
                node = getattr(browser, root_id, None)
                if node:
                    tree.append({"name": node.name, "is_folder": node.is_folder})
            self._send_response(client, tree)
        except Exception as e:
            self._send_error(client, f"Get browser tree err: {e}")

    def _do_get_browser_items_at_path(self, args):
        params, client = args
        try:
            path = params.get("path", "")
            node = self._traverse_browser_path(path)
            if not node:
                self._send_error(client, f"Path '{path}' not found in Ableton Browser.")
                return
                
            items = []
            for child in node.children:
                items.append({"name": child.name, "is_folder": child.is_folder})
                
            self._send_response(client, items)
        except Exception as e:
            self._send_error(client, f"Get browser items err: {e}")

    def _traverse_browser_path(self, path):
        parts = [p.strip() for p in path.split("/") if p.strip()]
        if not parts:
            return None
            
        browser = self.application().browser
        
        # Mapping for the root nodes according to Live.Browser
        root_map = {
            "Sounds": browser.sounds,
            "Drums": browser.drums,
            "Instruments": browser.instruments,
            "Audio Effects": browser.audio_effects,
            "MIDI Effects": browser.midi_effects,
            "Max for Live": getattr(browser, "max_for_live", None),
            "Plug-ins": browser.plugins,
            "Packs": browser.packs,
            "User Library": browser.user_library
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


    def _do_inject_midi_to_new_clip(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index", 0)
            length = params.get("length", 4.0)
            notes_req = params.get("notes", [])
            
            if t_idx >= len(self.song().tracks):
                self._send_error(client, "Track index out of bounds")
                return
                
            track = self.song().tracks[t_idx]
            
            open_slot_idx = -1
            for i, slot in enumerate(track.clip_slots):
                if not slot.has_clip:
                    open_slot_idx = i
                    break
                    
            if open_slot_idx == -1:
                self._send_error(client, "No empty clip slots available on the track.")
                return
                
            slot = track.clip_slots[open_slot_idx]
            slot.create_clip(length)
            clip = slot.clip
            
            if notes_req and clip:
                notes_to_add = tuple(Live.Clip.MidiNoteSpecification(
                    pitch=n["pitch"],
                    start_time=n["start_time"],
                    duration=n["duration"],
                    velocity=n["velocity"],
                    mute=False
                ) for n in notes_req)
                clip.add_new_notes(notes_to_add)
                
            self._send_response(client, {"status": "success", "clip_slot_index": open_slot_idx})
        except Exception as e:
            self._send_error(client, f"Inject midi err: {e}")

    def _do_load_device(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index", 0)
            path = params.get("browser_path", "")
            
            node = self._traverse_browser_path(path)
            if not node:
                self._send_error(client, f"Device '{path}' not found in Ableton Browser.")
                return
            
            track = self.song().tracks[t_idx]
            self.song().view.selected_track = track
            self.application().browser.load_item(node)
            self.log_message(f"Loaded {path} onto track {t_idx}")
            self._send_response(client, "ok")
        except Exception as e:
            self.log_message(f"Load device err: {e}")
            self._send_error(client, f"Load device err: {e}")

    def _do_load_drum_kit(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index", 0)
            path = params.get("drum_kit_path", "")
            
            # The structure for drum kits allows treating them identically to generic load_item
            node = self._traverse_browser_path(path)
            if not node:
                self._send_error(client, f"Drum Kit '{path}' not found in Ableton Browser.")
                return
            
            self.song().view.selected_track = self.song().tracks[t_idx]
            self.application().browser.load_item(node)
            self.log_message(f"Loaded drum kit {path} onto track {t_idx}")
            self._send_response(client, "ok")
        except Exception as e:
            self.log_message(f"Load drum kit err: {e}")
            self._send_error(client, f"Load drum kit err: {e}")

    # --- Advanced Editing Additions ---
    
    def _do_get_notes_from_clip(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            
            if t_idx >= len(self.song().tracks):
                self._send_error(client, "Track index out of bounds")
                return
            track = self.song().tracks[t_idx]
            if c_idx >= len(track.clip_slots):
                self._send_error(client, "Clip slot index out of bounds")
                return
            clip = track.clip_slots[c_idx].clip
            if not clip:
                self._send_response(client, [])
                return
                
            out_notes = []
            if clip:
                notes = clip.get_notes_extended(int(0), int(128), float(0.0), float(9999.0))
                for n in notes:
                    out_notes.append({
                        "pitch": n.pitch,
                        "start_time": n.start_time,
                        "duration": n.duration,
                        "velocity": n.velocity
                    })
            self._send_response(client, out_notes)
        except Exception as e:
            self._send_error(client, f"Get notes err: {e}")

    def _do_delete_notes_from_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            notes_req = params.get("notes", [])
            
            if t_idx >= len(self.song().tracks): return
            track = self.song().tracks[t_idx]
            if c_idx >= len(track.clip_slots): return
            clip = track.clip_slots[c_idx].clip
            if not clip: return
            
            # Remove matching pitch and start_time precisely
            for n in notes_req:
                pitch = n.get("pitch")
                start_time = n.get("start_time")
                if pitch is not None and start_time is not None:
                    # using tiny time_span of 0.01 to isolate exact note start
                    # C++ signature: clip.remove_notes_extended(int from_pitch, int pitch_span, double from_time, double time_span)
                    clip.remove_notes_extended(int(pitch), int(1), float(start_time), float(0.01))
        except Exception as e:
            self.log_message(f"Delete notes err: {e}")

    def _do_delete_track(self, params):
        try:
            t_idx = params.get("track_index", 0)
            if t_idx >= 0 and t_idx < len(self.song().tracks):
                self.song().delete_track(t_idx)
            else:
                self.log_message(f"Delete track err: Invalid index {t_idx}")
        except Exception as e:
            self.log_message(f"Delete track err: {e}")

    def _do_delete_clip(self, params):
        try:
            t_idx = params.get("track_index", 0)
            c_idx = params.get("clip_slot_index", 0)
            if t_idx >= len(self.song().tracks): return
            track = self.song().tracks[t_idx]
            if c_idx >= len(track.clip_slots): return
            track.clip_slots[c_idx].delete_clip()
        except Exception as e:
            self.log_message(f"Delete clip err: {e}")

    # --- Device & Mix Parameters Additions ---

    def _do_get_track_devices(self, args):
        params, client = args
        try:
            t_idx = int(params.get("track_index", 0))
            track = self.song().tracks[t_idx]
            
            out_devices = []
            for i, d in enumerate(track.devices):
                out_devices.append({
                    "index": i,
                    "name": str(d.name)
                })
            self._send_response(client, out_devices)
        except IndexError:
            self._send_error(client, f"Track index {params.get('track_index', 0)} out of bounds. Tracks are 0-indexed.")
        except Exception as e:
            self._send_error(client, f"Get track devices err: {str(e)}")

    def _do_get_device_parameters(self, args):
        params, client = args
        try:
            t_idx = int(params.get("track_index", 0))
            d_idx = int(params.get("device_index", 0))
            
            track = self.song().tracks[t_idx]
            device = track.devices[d_idx]
            
            out_params = []
            for i, p in enumerate(device.parameters):
                out_params.append({
                    "index": i,
                    "name": str(p.name),
                    "value": float(p.value),
                    "display_value": str(p),
                    "min": float(p.min),
                    "max": float(p.max)
                })
            self._send_response(client, {"device_name": str(device.name), "parameters": out_params})
        except IndexError:
            self._send_error(client, f"Track or Device index out of bounds. t_idx={params.get('track_index')} d_idx={params.get('device_index')}")
        except Exception as e:
            self._send_error(client, f"Get device params err: {str(e)}")

    def _do_set_device_parameter(self, args):
        params, client = args
        try:
            t_idx = int(params.get("track_index", 0))
            d_idx = int(params.get("device_index", 0))
            p_name = params.get("parameter_name", "")
            val = params.get("value", 0.0)
            
            track = self.song().tracks[t_idx]
            device = track.devices[d_idx]
            
            target_name = re.sub(r'[^a-z0-9]', '', str(p_name).lower())
            if not target_name:
                self._send_error(client, "Parameter name cannot be empty")
                return
            
            best_match = None
            
            # 1. Exact match (case-insensitive, fully alphanumeric)
            exact_matches = [p for p in device.parameters if re.sub(r'[^a-z0-9]', '', str(p.name).lower()) == target_name]
            if len(exact_matches) == 1:
                best_match = exact_matches[0]
            elif len(exact_matches) > 1:
                names = [str(p.name) for p in exact_matches]
                self._send_error(client, f"Ambiguous parameter name. Multiple matches found: {names}. Please provide the exact parameter name.")
                return
            
            # 2. Substring match
            if not best_match:
                sub_matches = []
                for p in device.parameters:
                    p_norm = re.sub(r'[^a-z0-9]', '', str(p.name).lower())
                    if target_name in p_norm or p_norm in target_name:
                        sub_matches.append(p)
                
                if len(sub_matches) == 1:
                    best_match = sub_matches[0]
                elif len(sub_matches) > 1:
                    names = [str(p.name) for p in sub_matches]
                    self._send_error(client, f"Ambiguous parameter name. Multiple matches found: {names}. Please provide the exact parameter name.")
                    return
            
            # 3. Synonym mapping
            if not best_match:
                synonyms = {
                    "cutoff": ["freq", "filterfreq"],
                    "freq": ["cutoff"],
                    "volume": ["gain", "out", "level"],
                    "gain": ["volume", "level"],
                    "level": ["volume", "gain"]
                }
                
                mapped_targets = synonyms.get(target_name, [])
                syn_matches = []
                for p in device.parameters:
                    p_norm = re.sub(r'[^a-z0-9]', '', str(p.name).lower())
                    for syn in mapped_targets:
                        if syn == p_norm or syn in p_norm or p_norm in syn:
                            if p not in syn_matches:
                                syn_matches.append(p)
                                
                if len(syn_matches) == 1:
                    best_match = syn_matches[0]
                elif len(syn_matches) > 1:
                    names = [str(p.name) for p in syn_matches]
                    self._send_error(client, f"Ambiguous parameter name. Multiple matches found: {names}. Please provide the exact parameter name.")
                    return

            if not best_match:
                self._send_error(client, f"Parameter '{p_name}' not found on device '{device.name}'.")
                return

            # Safety clamp and assign
            clampped_val = max(float(best_match.min), min(float(best_match.max), float(val)))
            best_match.value = clampped_val
            self._send_response(client, str(best_match))
        except IndexError:
            self._send_error(client, f"Track or Device index out of bounds. t_idx={params.get('track_index')} d_idx={params.get('device_index')}")
        except Exception as e:
            self.log_message(f"Set device param err: {str(e)}")
            self._send_error(client, f"Set device param err: {str(e)}")

    def _do_set_track_mixer(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index")
            if t_idx is None:
                self._send_error(client, "track_index is required")
                return
            t_idx = int(t_idx)
            
            if t_idx < 0 or t_idx >= len(self.song().tracks):
                self._send_error(client, f"Track index {t_idx} out of bounds")
                return
                
            track = self.song().tracks[t_idx]
            
            if "volume" in params:
                try:
                    vol = float(params["volume"])
                    track.mixer_device.volume.value = max(0.0, min(1.0, vol))
                except Exception as e:
                    self.log_message(f"Error setting volume: {e}")
                    
            if "panning" in params:
                try:
                    pan = float(params["panning"])
                    track.mixer_device.panning.value = max(-1.0, min(1.0, pan))
                except Exception as e:
                    self.log_message(f"Error setting panning: {e}")
                    
            if "mute" in params:
                try:
                    mute_val = bool(params["mute"])
                    track.mute = mute_val
                except Exception as e:
                    self.log_message(f"Error setting mute: {e}")
                    
            self._send_response(client, "ok")
        except Exception as e:
            self.log_message(f"Set track mixer err: {str(e)}")
            self._send_error(client, f"Set track mixer err: {str(e)}")

def create_instance(c_instance):
    return GeminiRemoteScript(c_instance)
