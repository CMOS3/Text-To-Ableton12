import os
from dotenv import load_dotenv
load_dotenv()
import logging

# Load environment variables at the very top
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import sys
import os

# Ensure the root directory is in the python path to allow direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.gemini_client import GeminiAbletonClient
from backend import schema
from backend.mcp_proxy import proxy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ableton MCP Backend")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize single client instance
try:
    gemini_client = GeminiAbletonClient()
except Exception as e:
    logger.error(f"Failed to initialize Gemini Client: {e}")
    gemini_client = None


class ChatResponse(BaseModel):
    response: str
    model_used: str
    input_tokens: int
    output_tokens: int

@app.post("/chat")
async def chat_endpoint(req: schema.ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="Gemini Client not configured. Check API key.")
    
    return StreamingResponse(gemini_client.chat(req.prompt, req.chat_history, req.require_approval), media_type="application/x-ndjson")

# --- Direct API Endpoints for UI Tester ---

@app.post("/api/action-response")
async def action_response(req: schema.ApprovalRequest):
    if gemini_client:
        gemini_client.is_approved = req.approved
        gemini_client.approval_event.set()
        return {"status": "success"}
    return {"status": "error", "message": "Gemini client not initialized"}

@app.get("/api/ping")
def ping():
    try:
        return proxy.ping()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/session")
def get_session():
    try:
        return proxy.request_state("get_session_info")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/session-context")
def get_session_context():
    try:
        response = proxy.request_state("get_session_info")
        if response.get("status") == "success":
            info = response.get("data", {}).get("result", {})
            return {"status": "success", "data": info}
        else:
            return response
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/tempo")
def set_tempo(req: schema.TempoRequest):
    try:
        return proxy.send_command("set_tempo", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/playback/start")
def start_playback():
    try:
        return proxy.send_command("start_playback")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/playback/stop")
def stop_playback():
    try:
        return proxy.send_command("stop_playback")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/track/create")
def create_track(req: schema.TrackNameRequest):
    try:
        return proxy.send_command("create_midi_track", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/track/rename")
def rename_track(req: schema.TrackIndexNameRequest):
    try:
        return proxy.send_command("set_track_name", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/browser/tree")
def get_browser_tree():
    try:
        return proxy.request_state("get_browser_tree")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/browser/items")
def get_browser_items(req: schema.BrowserItemsRequest):
    try:
        return proxy.request_state("get_browser_items_at_path", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/track/load_device")
def load_device(req: schema.LoadDeviceRequest):
    try:
        return proxy.send_command("load_instrument_or_effect", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/track/load_drum_kit")
def load_drum_kit(req: schema.LoadDrumKitRequest):
    try:
        return proxy.send_command("load_drum_kit", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/clip/rename")
def rename_clip(req: schema.SetClipNameRequest):
    try:
        return proxy.send_command("set_clip_name", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/clip/stop")
def stop_clip(req: schema.StopClipRequest):
    try:
        return proxy.send_command("stop_clip", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/clip/notes")
def get_notes_from_clip(req: schema.ClipActionRequest):
    try:
        return proxy.request_state("get_notes_from_clip", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/clip/notes")
def delete_notes_from_clip(req: schema.DeleteNotesRequest):
    try:
        return proxy.send_command("delete_notes_from_clip", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/track")
def delete_track(req: schema.TrackIndexRequest):
    try:
        return proxy.send_command("delete_track", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/clip")
def delete_clip(req: schema.ClipActionRequest):
    try:
        return proxy.send_command("delete_clip", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/device/parameters")
def get_device_parameters(req: schema.DeviceIndexRequest):
    try:
        return proxy.request_state("get_device_parameters", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.put("/api/device/parameter")
def set_device_parameter_by_name(req: schema.SetDeviceParameterByNameRequest):
    try:
        return proxy.send_command("set_device_parameter", req.model_dump())
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
