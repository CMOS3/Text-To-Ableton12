from pydantic import BaseModel, Field
from typing import List, Optional

# ---- Note Models ----
class NoteSchema(BaseModel):
    pitch_name: str = Field(..., description="Semantic pitch name (e.g., 'C1', 'Eb2', 'F#3'). Use flats (b) or sharps (#).")
    pitch: Optional[int] = Field(None, description="MIDI pitch (0-127). Derived automatically by backend, leave empty.")
    start_time: float = Field(..., description="Start time STRICTLY in beats. E.g., beat 1 = 0.0, beat 2 = 1.0.")
    duration: float = Field(..., description="Duration STRICTLY in beats. 1 bar = 4.0 beats (in 4/4).")
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
    length: float = Field(4.0, description="Length of the new clip STRICTLY in beats. E.g., for a 4-bar clip in 4/4 time, use 16.0.")

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
    device_index: int

class SetDeviceParameterRequest(BaseModel):
    track_index: int
    device_index: int
    parameter_index: int
    value: float
