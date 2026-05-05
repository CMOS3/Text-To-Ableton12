from _Framework.ControlSurface import ControlSurface
import socket
import threading
import json
import queue
import re
import hashlib

from .handlers import SessionMixin, TrackMixin, ClipMixin, BrowserMixin, DeviceMixin

class GeminiRemoteScript(
    ControlSurface,
    SessionMixin,
    TrackMixin,
    ClipMixin,
    BrowserMixin,
    DeviceMixin,
):
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
            self.server.bind(("127.0.0.1", 9877))
            self.server.listen(5)
            self.log_message("Ableton MCP Listener started on 127.0.0.1:9877")

            while True:
                try:
                    client, addr = self.server.accept()
                    threading.Thread(
                        target=self.handle_client, args=(client,), daemon=True
                    ).start()
                except Exception as e:
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

                for line in data.decode("utf-8").strip().split("\n"):
                    if not line:
                        continue
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

    def _send_response(self, client, data, apply_toon=True):
        try:
            if apply_toon and isinstance(data, (dict, list, tuple)):
                data = self._to_toon(data)
            response = json.dumps({"result": data}) + "\n"
            client.sendall(response.encode("utf-8"))
        except Exception as e:
            self.log_message(f"Error sending response: {e}")

    def _send_error(self, client, error_msg):
        try:
            response = json.dumps({"error": error_msg}) + "\n"
            client.sendall(response.encode("utf-8"))
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
        elif method == "get_session_info" or method == "get_track_list":
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
            self.execute_safely(
                self._do_set_track_name,
                (params.get("track_index", 0), params.get("name", "")),
            )
            self._send_response(client, "ok")
        elif method == "select_track":
            self.execute_safely(self._do_select_track, params.get("track_name", ""))
            self._send_response(client, "ok")
        elif method == "arm_track":
            self.execute_safely(
                self._do_arm_track,
                (params.get("track_name", ""), params.get("arm", True)),
            )
            self._send_response(client, "ok")

        # --- Clip Operations ---
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

    def _do_ping(self, client):
        self._send_response(client, "pong")

    def _generate_etag(self, data_str):
        return hashlib.md5(data_str.encode("utf-8")).hexdigest()[:8]

    def _to_toon(self, obj):
        """Basic TOON (Token-Oriented Object Notation) compression"""
        if isinstance(obj, dict):
            return (
                "{" + ",".join(f"{k}:{self._to_toon(v)}" for k, v in obj.items()) + "}"
            )
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return "[" + ",".join(self._to_toon(v) for v in obj) + "]"
        elif isinstance(obj, str):
            if re.match(r"^[a-zA-Z0-9_]+$", obj):
                return obj
            escaped = obj.replace('"', '\\"')
            return f'"{escaped}"'
        elif isinstance(obj, bool):
            return "T" if obj else "F"
        elif obj is None:
            return "N"
        else:
            if isinstance(obj, float):
                return f"{obj:.3f}".rstrip("0").rstrip(".")
            return str(obj)

def create_instance(c_instance):
    return GeminiRemoteScript(c_instance)
