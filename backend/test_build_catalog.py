import pytest
from pathlib import Path
from backend.build_catalog import extract_adg_macros, calculate_md5
from backend.gemini.tools import AbletonToolMixin

# Skeleton for testing XML extraction logic
def test_extract_adg_macros_happy_path(tmp_path):
    # Setup: Create a dummy ADG file (gzip compressed XML)
    import gzip
    adg_file = tmp_path / "dummy.adg"
    dummy_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Ableton>
        <MacroDisplayNames.0 Value="Cutoff" />
        <MacroDisplayNames.1 Value="Macro 2" /> <!-- Should be ignored -->
        <MacroAnnotations.0 Value="0=Low, 127=High" />
    </Ableton>
    '''
    with gzip.open(adg_file, 'wb') as f:
        f.write(dummy_xml)

    # Action
    names, annotations = extract_adg_macros(adg_file)

    # Observation
    assert names[0] == "Cutoff"
    assert 1 not in names  # Macro 2 should be filtered out
    assert annotations[0] == "0=Low, 127=High"

def test_md5_calculation(tmp_path):
    # Setup
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    
    # Action
    hash_val = calculate_md5(test_file)
    
    # Observation
    assert hash_val == "5eb63bbbe01eeed093cb22bb8f5acdc3"

def test_load_preset_rack_tool_wrapper():
    # Setup
    class DummyTool(AbletonToolMixin):
        def load_instrument_or_effect(self, track_index: int, browser_path: str) -> str:
            return f"Loaded {browser_path} on track {track_index}"
            
    tool = DummyTool()
    
    # Action
    result = tool.load_preset_rack(1, "AI_Archetype_Analog")
    
    # Observation
    assert result == "Loaded User Library/Presets/Text-to-Ableton/AI_Archetype_Analog.adg on track 1"
