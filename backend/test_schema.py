import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydantic import ValidationError
from schema import (
    SetDeviceParameterBatchRequest,
    FetchResourceRequest,
    CreateClipRequest,
    NoteSchema,
    TweakSchema
)

def test_sound_design_request_valid():
    payload = {
        "track_index": 0,
        "device_index": 0,
        "parameters": [
            {"parameter_name": "Filter Freq", "value": 0.5},
            {"parameter_name": "Resonance", "value": 0.8}
        ]
    }
    req = SetDeviceParameterBatchRequest(**payload)
    assert req.track_index == 0
    assert req.device_index == 0
    assert len(req.parameters) == 2
    assert req.parameters[0].parameter_name == "Filter Freq"
    assert req.parameters[0].value == 0.5

def test_sound_design_request_invalid_tweaks():
    payload = {
        "track_index": 0,
        "device_index": 0,
        "parameters": {
            "Filter Freq": 0.5
        }
    }
    try:
        SetDeviceParameterBatchRequest(**payload)
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
