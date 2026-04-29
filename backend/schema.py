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
    require_approval: bool = True

class ApprovalRequest(BaseModel):
    approved: bool

class TrackNameRequest(BaseModel):
    track_name: str

class TrackIndexNameRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    name: str

class TempoRequest(BaseModel):
    tempo: float = Field(..., description="BPM, e.g. 120.0")

class CreateClipRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    clip_slot_index: int
    length: float = Field(4.0, description="Length of the new clip STRICTLY in beats. E.g., for a 4-bar clip in 4/4 time, use 16.0.")

class SetClipNameRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    clip_slot_index: int
    name: str

class AddNotesRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    clip_slot_index: int
    notes: List[NoteSchema]

class GetNotesFromClipRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    clip_slot_index: int


class InjectMidiRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    length: float = Field(4.0, description="Length of the new clip STRICTLY in beats. E.g., for a 4-bar clip in 4/4 time, use 16.0.")
    notes: List[NoteSchema]

class BrowserItemsRequest(BaseModel):
    path: str = Field(..., description="Path to a folder in the browser, e.g. 'Packs/Lost and Found'.")

class LoadDeviceRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    browser_path: str = Field(..., description="Path to the instrument or effect in the browser.")

class LoadDrumKitRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    drum_kit_path: str

class GetTrackDevicesRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")

class GetTrackInfoRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")

class DeleteNotesRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    clip_slot_index: int
    notes: List[NoteSchema]

class DeviceIndexRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    device_index: int

class SetDeviceParameterByNameRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track. CRITICAL: If the user asks for 'Track 1', you MUST pass 0. 'Track 2' is 1, etc.")
    device_index: int
    parameter_name: str
    value: float

class SetTrackVolumeByNameRequest(BaseModel):
    track_name: str
    gain_db: float

class MixTrackRequest(BaseModel):
    track_index: int = Field(..., description="The 0-based index of the target track (or return track).")
    volume: Optional[float] = Field(None, description="Volume level from 0.0 to 1.0 (where ~0.85 is 0dB). Matches the volume shown in the session state.")
    panning: Optional[float] = Field(None, description="Panning from -1.0 (Left) to 1.0 (Right).")
    mute: Optional[bool] = Field(None, description="Set to true to mute the track, false to unmute.")

class TweakSchema(BaseModel):
    parameter_name: str = Field(..., description="Name of the parameter to tweak.")
    value: float = Field(..., description="New value for the parameter (0.0 to 1.0).")

class SoundDesignRequest(BaseModel):
    track_name: str
    device_name: str
    tweaks: List[TweakSchema] = Field(..., description="List of parameter tweaks to apply.")

class SupervisorSoundDesign(BaseModel):
    track_name: str
    device_name: str
    intent: str = Field(..., description="The sound design goal, e.g. 'Make it a dark reese bass'")

class SupervisorInjectMidi(BaseModel):
    track_index: int
    length: float
    intent: str = Field(..., description="The musical goal, e.g. 'A 4-to-the-floor kick drum pattern'")

class FetchResourceRequest(BaseModel):
    uri: str = Field(..., description="The MCP resource URI to fetch, e.g., 'ableton://tracks/1/state'")
