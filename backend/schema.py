from pydantic import BaseModel, Field
from typing import List, Optional

# ---- Note Models ----
class NoteSchema(BaseModel):
    pitch: int = Field(..., description="MIDI pitch (0-127). Middle C is 60.")
    start_time: float = Field(..., description="Start time in beats.")
    duration: float = Field(..., description="Duration in beats.")
    velocity: int = Field(100, description="Velocity (1-127).")

# ---- Request Models for FastAPI & Gemini Tools ----

class ChatRequest(BaseModel):
    prompt: str
    chat_history: Optional[List[dict]] = Field(default_factory=list)

class TrackNameRequest(BaseModel):
    track_name: str

class TrackIndexNameRequest(BaseModel):
    track_index: int
    name: str

class TrackArmRequest(BaseModel):
    track_name: str
    arm: bool = True

class TempoRequest(BaseModel):
    tempo: float = Field(..., description="BPM, e.g. 120.0")

class CreateClipRequest(BaseModel):
    track_index: int
    clip_slot_index: int
    length: float = Field(4.0, description="Length of the new clip in beats.")

class SetClipNameRequest(BaseModel):
    track_index: int
    clip_slot_index: int
    name: str

class AddNotesRequest(BaseModel):
    track_index: int
    clip_slot_index: int
    notes: List[NoteSchema]

class ClipActionRequest(BaseModel):
    track_index: int
    clip_slot_index: int

class StopClipRequest(BaseModel):
    track_index: int
    clip_slot_index: int

class BrowserPathRequest(BaseModel):
    path: str

class LoadDeviceRequest(BaseModel):
    track_index: int
    browser_path: str = Field(..., description="Path to the instrument or effect in the browser.")

class LoadDrumKitRequest(BaseModel):
    track_index: int
    drum_kit_path: str

class TrackIndexRequest(BaseModel):
    track_index: int

class DeleteNotesRequest(BaseModel):
    track_index: int
    clip_slot_index: int
    notes: List[NoteSchema]

class DeviceIndexRequest(BaseModel):
    track_index: int
    device_index: int = 0

class SetDeviceParameterRequest(BaseModel):
    track_index: int
    device_index: int
    parameter_index: int
    value: float
