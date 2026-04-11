import socket
import json

class MCPProxy:
    def __init__(self, host="127.0.0.1", port=9877):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        if self.sock is not None:
            return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2.0)
            self.sock.connect((self.host, self.port))
            # Remove timeout for persistent connection
            self.sock.settimeout(None) 
            return True
        except Exception as e:
            if self.sock:
                self.sock.close()
                self.sock = None
            raise e

    def send_command(self, method: str, params: dict = None) -> str:
        payload = {"method": method, "params": params or {}}
        try:
            self.connect()
            self.sock.sendall(json.dumps(payload).encode('utf-8'))
            return f"Successfully sent '{method}' to Ableton MCP Server."
        except ConnectionRefusedError:
            self._reset_connection()
            return f"Connection refused: The Ableton MCP Server is not running on {self.host}:{self.port}."
        except Exception as e:
            self._reset_connection()
            return f"Error communicating with Ableton MCP Server: {str(e)}"

    def request_state(self, method: str, params: dict = None) -> str:
        payload = {"method": method, "params": params or {}}
        try:
            self.connect()
            self.sock.sendall(json.dumps(payload).encode('utf-8'))
            data = self.sock.recv(8192)
            if data:
                return data.decode('utf-8')
            return "No data received"
        except Exception as e:
            self._reset_connection()
            return f"Error communicating with Ableton MCP Server: {str(e)}"

    def ping(self) -> str:
        return self.send_command("ping")
            
    def _reset_connection(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None

proxy = MCPProxy()
