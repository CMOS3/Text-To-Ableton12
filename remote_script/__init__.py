from _Framework.ControlSurface import ControlSurface
import socket
import threading
import json

class GeminiRemoteScript(ControlSurface):
    def __init__(self, c_instance):
        super().__init__(c_instance)
        self.mcp_thread = threading.Thread(target=self.start_mcp_listener, daemon=True)
        self.mcp_thread.start()

    def start_mcp_listener(self):
        # Strict binding to 127.0.0.1 as per safety rules
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('127.0.0.1', 9877))
            server.listen(5)
            self.log_message("Ableton MCP Listener started on 127.0.0.1:9877")
            
            while True:
                try:
                    client, addr = server.accept()
                    # Start a handler thread for the connection
                    threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
                except Exception as e:
                    self.log_message(f"Accept error: {e}")
        except Exception as e:
            self.log_message(f"Could not bind to port 9877: {e}")

    def handle_client(self, client):
        try:
            while True:
                data = client.recv(4096)
                if not data:
                    break
                
                try:
                    payload = json.loads(data.decode('utf-8'))
                    # Check for 'method' or fallback to 'type' for backward compatibility
                    method = payload.get("method") or payload.get("type")
                    params = payload.get("params", {})
                    
                    if method == "ping":
                        self.log_message("MCP: Received Ping")
                    elif method == "create_midi_track":
                        track_name = params.get("track_name", "Gemini MIDI Track")
                        # Schedule to run on Ableton's main thread
                        self.schedule_message(1, self._do_create_midi_track, track_name)
                    elif method == "get_track_list":
                        self.schedule_message(1, self._do_get_track_list, client)
                    elif method == "select_track":
                        track_name = params.get("track_name", "")
                        self.schedule_message(1, self._do_select_track, track_name)
                    elif method == "arm_track":
                        track_name = params.get("track_name", "")
                        arm = params.get("arm", True)
                        self.schedule_message(1, self._do_arm_track, (track_name, arm))
                    else:
                        self.log_message(f"MCP: Unknown method '{method}'")
                except Exception as e:
                    self.log_message(f"MCP Dispatch error: {e}")
        except Exception as e:
            self.log_message(f"MCP Connection error: {e}")
        finally:
            client.close()

    def _do_get_track_list(self, client):
        try:
            track_names = [track.name for track in self.song().tracks]
            response = json.dumps({"result": track_names})
            client.sendall(response.encode('utf-8'))
            self.log_message(f"Sent track list: {track_names}")
        except Exception as e:
            self.log_message(f"Error getting track list: {e}")
            try:
                client.sendall(json.dumps({"error": str(e)}).encode('utf-8'))
            except:
                pass

    def _do_create_midi_track(self, track_name):
        try:
            self.song().create_midi_track(-1)
            # song().tracks is a tuple, access the last element
            new_track = self.song().tracks[-1]
            new_track.name = track_name
            self.log_message(f"Successfully created MIDI track: {track_name}")
        except Exception as e:
            self.log_message(f"Error creating MIDI track: {e}")

    def _do_select_track(self, track_name):
        try:
            for track in self.song().tracks:
                if track.name == track_name:
                    self.song().view.selected_track = track
                    self.log_message(f"Selected track: {track_name}")
                    return
            self.log_message(f"Track not found to select: {track_name}")
        except Exception as e:
            self.log_message(f"Error selecting track: {e}")

    def _do_arm_track(self, args):
        try:
            track_name, arm = args
            for track in self.song().tracks:
                if track.name == track_name:
                    if track.can_be_armed:
                        track.arm = arm
                        self.log_message(f"Armed track ({arm}): {track_name}")
                    else:
                        self.log_message(f"Track cannot be armed: {track_name}")
                    return
            self.log_message(f"Track not found to arm: {track_name}")
        except Exception as e:
            self.log_message(f"Error arming track: {e}")

def create_instance(c_instance):
    return GeminiRemoteScript(c_instance)
