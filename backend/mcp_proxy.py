import socket
import json
import logging

logger = logging.getLogger(__name__)

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

    def _create_payload(self, method: str, params: dict = None) -> bytes:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        # Add newline delimiter just in case the server uses readline()
        return (json.dumps(payload) + "\n").encode('utf-8')

    def send_command(self, method: str, params: dict = None) -> dict:
        """Sends a command and attempts to read an ack response."""
        try:
            self.connect()
            self.sock.settimeout(5.0) # Set timeout so we don't hang forever
            self.sock.sendall(self._create_payload(method, params))
            
            # Try to read the acknowledgment
            try:
                data = self.sock.recv(65536)
                if data:
                    decoded = data.decode('utf-8').strip()
                    try:
                        return {"status": "success", "data": json.loads(decoded)}
                    except json.JSONDecodeError:
                        return {"status": "success", "message": decoded}
            except socket.timeout:
                pass # It's fine if command doesn't return an ack immediately
            finally:
                self.sock.settimeout(None) # Restore persistent connection state
                
            return {"status": "success", "message": f"Successfully sent '{method}'"}
        except ConnectionRefusedError:
            self._reset_connection()
            return {"status": "error", "message": f"Connection refused: Ableton MCP Server not running on {self.host}:{self.port}."}
        except Exception as e:
            self._reset_connection()
            return {"status": "error", "message": f"Error communicating with Ableton MCP Server: {str(e)}"}

    def request_state(self, method: str, params: dict = None) -> dict:
        """Requests state and attempts to parse the JSON response."""
        try:
            self.connect()
            self.sock.settimeout(5.0) # Set timeout so we don't hang forever
            self.sock.sendall(self._create_payload(method, params))
            
            data = self.sock.recv(65536) # Read response
            self.sock.settimeout(None) # Restore persistent connection state
            
            if data:
                decoded = data.decode('utf-8').strip()
                try:
                    return {"status": "success", "data": json.loads(decoded)}
                except json.JSONDecodeError:
                    return {"status": "success", "data": decoded}
            return {"status": "error", "message": "No data received"}
        except socket.timeout:
            self._reset_connection()
            return {"status": "error", "message": "Request timed out waiting for Ableton response."}
        except Exception as e:
            self._reset_connection()
            return {"status": "error", "message": f"Error communicating with Ableton MCP Server: {str(e)}"}

    def ping(self) -> dict:
        return self.send_command("ping")
            
    def _reset_connection(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None

proxy = MCPProxy()
