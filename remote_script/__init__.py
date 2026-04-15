from _Framework.ControlSurface import ControlSurface
import socket
import threading
import json
import queue
import Live

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
            self.execute_safely(self._do_get_browser_items_at_path, (params.get("path", ""), client))
        elif method == "load_instrument_or_effect":
            self.execute_safely(self._do_load_device, params)
            self._send_response(client, "ok")
        elif method == "load_drum_kit":
            self.execute_safely(self._do_load_drum_kit, params)
            self._send_response(client, "ok")
            
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
        elif method == "get_device_parameters":
            self.execute_safely(self._do_get_device_parameters, (params, client))
        elif method == "set_device_parameters":
            self.execute_safely(self._do_set_device_parameters, params)
            self._send_response(client, "ok")
            
        else:
            self.log_message(f"MCP: Unknown method '{method}'")

    # ---- Handlers ----
    def _do_ping(self, client):
        self._send_response(client, "pong")

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
                    
                tracks_info.append({
                    "index": i, 
                    "name": track.name, 
                    "is_armed": track.arm if track.can_be_armed else False,
                    "volume": vol,
                    "panning": pan
                })
            
            info = {
                "tempo": self.song().tempo,
                "is_playing": self.song().is_playing,
                "tracks": tracks_info
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

    def _do_get_browser_items_at_path(self, args):
        path, client = args
        try:
            node = self._traverse_browser_path(path)
            if not node:
                self._send_error(client, f"Path not found: {path}")
                return
                
            items = []
            for child in node.children:
                items.append({"name": child.name, "is_folder": child.is_folder})
            self._send_response(client, items)
        except Exception as e:
            self._send_error(client, f"Get browser items err: {e}")

    def _do_load_device(self, params):
        try:
            t_idx = params.get("track_index", 0)
            path = params.get("browser_path", "")
            
            node = self._traverse_browser_path(path)
            if not node or node.is_folder:
                raise Exception(f"Device not found or is a folder: {path}")
            
            track = self.song().tracks[t_idx]
            self.application().browser.load_item(node)
            self.log_message(f"Loaded {path} onto track {t_idx}")
        except Exception as e:
            self.log_message(f"Load device err: {e}")

    def _do_load_drum_kit(self, params):
        try:
            t_idx = params.get("track_index", 0)
            path = params.get("drum_kit_path", "")
            
            # The structure for drum kits allows treating them identically to generic load_item
            node = self._traverse_browser_path(path)
            if not node or node.is_folder:
                raise Exception(f"Drum Kit not found or is a folder: {path}")
            
            self.song().view.selected_track = self.song().tracks[t_idx]
            self.application().browser.load_item(node)
            self.log_message(f"Loaded drum kit {path} onto track {t_idx}")
        except Exception as e:
            self.log_message(f"Load drum kit err: {e}")

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

    def _do_get_device_parameters(self, args):
        params, client = args
        try:
            t_idx = params.get("track_index", 0)
            d_idx = params.get("device_index", 0)
            
            if t_idx >= len(self.song().tracks):
                self._send_error(client, "Track index out of bounds")
                return
            track = self.song().tracks[t_idx]
            
            if d_idx >= len(track.devices):
                self._send_error(client, "Device index out of bounds")
                return
            device = track.devices[d_idx]
            
            out_params = []
            for i, p in enumerate(device.parameters):
                out_params.append({
                    "index": i,
                    "name": p.name,
                    "value": p.value,
                    "min": p.min,
                    "max": p.max
                })
            self._send_response(client, {"device_name": device.name, "parameters": out_params})
        except Exception as e:
            self._send_error(client, f"Get device params err: {e}")

    def _do_set_device_parameters(self, params):
        try:
            t_idx = params.get("track_index", 0)
            d_idx = params.get("device_index", 0)
            p_idx = params.get("parameter_index", 0)
            val = params.get("value", 0.0)
            
            if t_idx >= len(self.song().tracks): return
            track = self.song().tracks[t_idx]
            
            if d_idx >= len(track.devices): return
            device = track.devices[d_idx]
            
            if p_idx >= len(device.parameters): return
            param = device.parameters[p_idx]
            
            val = max(param.min, min(param.max, val))
            param.value = val
        except Exception as e:
            self.log_message(f"Set device param err: {e}")

def create_instance(c_instance):
    return GeminiRemoteScript(c_instance)

