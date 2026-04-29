import sys
import os
sys.path.append('d:/Sync/Dev/AbletonMCP_with_Gemini_API/backend')

from pydantic import ValidationError
from schema import (
    SoundDesignRequest,
    FetchResourceRequest,
    CreateClipRequest,
    NoteSchema,
    TweakSchema
)

def test_sound_design_request_valid():
    payload = {
        "track_name": "Lead Synth",
        "device_name": "Operator",
        "tweaks": [
            {"parameter_name": "Filter Freq", "value": 0.5},
            {"parameter_name": "Resonance", "value": 0.8}
        ]
    }
    req = SoundDesignRequest(**payload)
    assert req.track_name == "Lead Synth"
    assert req.device_name == "Operator"
    assert len(req.tweaks) == 2
    assert req.tweaks[0].parameter_name == "Filter Freq"
    assert req.tweaks[0].value == 0.5

def test_sound_design_request_invalid_tweaks():
    payload = {
        "track_name": "Lead Synth",
        "device_name": "Operator",
        "tweaks": {
            "Filter Freq": 0.5
        }
    }
    try:
        SoundDesignRequest(**payload)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass

def test_fetch_resource_request():
    payload = {
        "uri": "ableton://tracks/0/clips"
    }
    req = FetchResourceRequest(**payload)
    assert req.uri == "ableton://tracks/0/clips"

def test_create_clip_request():
    payload = {
        "track_index": 0,
        "clip_slot_index": 1,
        "length": 16.0
    }
    req = CreateClipRequest(**payload)
    assert req.track_index == 0
    assert req.clip_slot_index == 1
    assert req.length == 16.0

if __name__ == "__main__":
    test_sound_design_request_valid()
    test_sound_design_request_invalid_tweaks()
    test_fetch_resource_request()
    test_create_clip_request()
    print("All schema tests passed successfully.")
