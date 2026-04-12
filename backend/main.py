from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging

from .gemini_client import GeminiAbletonClient
from . import schema
from .mcp_proxy import proxy

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

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: schema.ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="Gemini Client not configured. Check API key.")
    
    try:
        response_text = gemini_client.chat(req.prompt)
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Direct API Endpoints for UI Tester ---

@app.get("/api/ping")
async def ping():
    return proxy.ping()

@app.get("/api/session")
async def get_session():
    return proxy.request_state("get_session_info")

@app.post("/api/tempo")
async def set_tempo(req: schema.TempoRequest):
    return proxy.send_command("set_tempo", req.model_dump())

@app.post("/api/playback/start")
async def start_playback():
    return proxy.send_command("start_playback")

@app.post("/api/playback/stop")
async def stop_playback():
    return proxy.send_command("stop_playback")

@app.post("/api/track/create")
async def create_track(req: schema.TrackNameRequest):
    return proxy.send_command("create_midi_track", req.model_dump())

@app.post("/api/track/rename")
async def rename_track(req: schema.TrackIndexNameRequest):
    return proxy.send_command("set_track_name", req.model_dump())

@app.get("/api/browser/tree")
async def get_browser_tree():
    return proxy.request_state("get_browser_tree")

@app.post("/api/browser/items")
async def get_browser_items(req: schema.BrowserPathRequest):
    return proxy.request_state("get_browser_items_at_path", req.model_dump())

@app.post("/api/track/load_device")
async def load_device(req: schema.LoadDeviceRequest):
    return proxy.send_command("load_instrument_or_effect", req.model_dump())

@app.post("/api/track/load_drum_kit")
async def load_drum_kit(req: schema.LoadDrumKitRequest):
    return proxy.send_command("load_drum_kit", req.model_dump())

@app.post("/api/clip/rename")
async def rename_clip(req: schema.SetClipNameRequest):
    return proxy.send_command("set_clip_name", req.model_dump())

@app.post("/api/clip/stop")
async def stop_clip(req: schema.StopClipRequest):
    return proxy.send_command("stop_clip", req.model_dump())

@app.post("/api/clip/notes")
async def get_notes_from_clip(req: schema.ClipActionRequest):
    return proxy.request_state("get_notes_from_clip", req.model_dump())

@app.delete("/api/clip/notes")
async def delete_notes_from_clip(req: schema.DeleteNotesRequest):
    return proxy.send_command("delete_notes_from_clip", req.model_dump())

@app.delete("/api/track")
async def delete_track(req: schema.TrackIndexRequest):
    return proxy.send_command("delete_track", req.model_dump())

@app.delete("/api/clip")
async def delete_clip(req: schema.ClipActionRequest):
    return proxy.send_command("delete_clip", req.model_dump())

@app.post("/api/device/parameters")
async def get_device_parameters(req: schema.DeviceIndexRequest):
    return proxy.request_state("get_device_parameters", req.model_dump())

@app.put("/api/device/parameter")
async def set_device_parameters(req: schema.SetDeviceParameterRequest):
    return proxy.send_command("set_device_parameters", req.model_dump())

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
