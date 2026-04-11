import os
import json
from dotenv import load_dotenv

from google import genai
from google.genai import types

from mcp_proxy import proxy

# Load environment variables
load_dotenv()

class GeminiAbletonClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        self.client = genai.Client(api_key=api_key)
        
        self.system_instruction = (
            "You are a session-aware Ableton expert. You MUST use the get_current_session_state "
            "tool to see existing tracks before creating new ones or when asked about the session state. "
            "You can now select and arm tracks. If a user says 'I want to record on the Bass track,' "
            "you should find the track, select it, and arm it for them."
        )
        
        self.model_name = "models/gemini-3.1-pro-preview-customtools"

    def test_ableton_connection(self) -> str:
        """
        Attempts to send a JSON 'ping' message to the Ableton MCP Server at 127.0.0.1:9877.
        """
        return proxy.ping()

    def get_current_session_state(self) -> str:
        """
        Retrieves the current tracks in the Ableton Live session, returning a JSON-encoded list of track names.
        """
        response = proxy.request_state("get_track_list")
        return f"Current session tracks: {response}"

    def create_midi_track(self, track_name: str) -> str:
        """
        Creates a new MIDI track in Ableton Live and sets its name.
        
        Args:
            track_name: The name to assign to the newly created MIDI track.
        """
        return proxy.send_command("create_midi_track", {"track_name": track_name})

    def select_track(self, track_name: str) -> str:
        """
        Selects (focuses) a track by name in Ableton Live.
        
        Args:
            track_name: The name of the track to select.
        """
        return proxy.send_command("select_track", {"track_name": track_name})

    def arm_track(self, track_name: str, arm: bool = True) -> str:
        """
        Arms or disarms a track for recording by name in Ableton Live.
        
        Args:
            track_name: The name of the track to arm.
            arm: True to arm, False to disarm. Defaults to True.
        """
        return proxy.send_command("arm_track", {"track_name": track_name, "arm": arm})

    def chat(self, user_prompt: str) -> str:
        """
        Executes a single-turn chat with the Gemini model.
        """
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=[self.test_ableton_connection, self.get_current_session_state, self.create_midi_track, self.select_track, self.arm_track],
        )
        
        # We explicitly turn off automatic tool execution to keep it purely single-turn and manually handle it 
        # for maximum token efficiency as requested.
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config
        )
        
        result_texts = []
        if response.function_calls:
            for fc in response.function_calls:
                if fc.name == "test_ableton_connection":
                    tool_result = self.test_ableton_connection()
                    result_texts.append(f"Model invoked tool '{fc.name}'.\nResult: {tool_result}")
                elif fc.name == "get_current_session_state":
                    tool_result = self.get_current_session_state()
                    result_texts.append(f"Model invoked tool '{fc.name}'.\nResult: {tool_result}")
                elif fc.name == "create_midi_track":
                    # Extract track_name from arguments
                    track_name = fc.args.get("track_name", "Gemini MIDI Track")
                    tool_result = self.create_midi_track(track_name)
                    result_texts.append(f"Model invoked tool '{fc.name}' with name '{track_name}'.\nResult: {tool_result}")
                elif fc.name == "select_track":
                    track_name = fc.args.get("track_name", "")
                    tool_result = self.select_track(track_name)
                    result_texts.append(f"Model invoked tool '{fc.name}' for track '{track_name}'.\nResult: {tool_result}")
                elif fc.name == "arm_track":
                    track_name = fc.args.get("track_name", "")
                    arm = fc.args.get("arm", True)
                    tool_result = self.arm_track(track_name, arm)
                    result_texts.append(f"Model invoked tool '{fc.name}' for track '{track_name}' (arm={arm}).\nResult: {tool_result}")
        
        if response.text:
            result_texts.append(response.text)
                
        return "\n".join(result_texts)
