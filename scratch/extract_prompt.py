import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.gemini_client import GeminiAbletonClient

client = GeminiAbletonClient()

try:
    session_info = client.get_session_info()
    print("--- SESSION INFO ---")
    print(session_info)
except Exception as e:
    print(f"Error getting session info: {e}")
