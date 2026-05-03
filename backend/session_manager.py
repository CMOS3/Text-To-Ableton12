import os
import json
import uuid
import time
from typing import List, Optional, Dict, Any

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "data", "sessions")

class SessionManager:
    def __init__(self):
        # Ensure the directory exists
        os.makedirs(SESSIONS_DIR, exist_ok=True)

    def _get_filepath(self, session_id: str) -> str:
        return os.path.join(SESSIONS_DIR, f"{session_id}.json")

    def create_session(self, title: str = "New Session", chat_history: List[Dict[str, Any]] = None, metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        timestamp = time.time()
        
        session_data = {
            "id": session_id,
            "title": title,
            "last_edited": timestamp,
            "chat_history": chat_history or [],
            "metrics": metrics or {
                "cost_flash": 0.0,
                "cost_pro": 0.0
            }
        }
        
        self.save_session(session_id, session_data)
        return session_data

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        session_data["last_edited"] = time.time()
        filepath = self._get_filepath(session_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        filepath = self._get_filepath(session_id)
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(SESSIONS_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # We only need the summary for the list
                        sessions.append({
                            "id": data.get("id"),
                            "title": data.get("title", "Untitled Session"),
                            "last_edited": data.get("last_edited", 0)
                        })
                except Exception:
                    pass
                    
        # Sort chronologically by last_edited descending (newest first)
        sessions.sort(key=lambda x: x["last_edited"], reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        filepath = self._get_filepath(session_id)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

# Global instance for the app
session_manager = SessionManager()
