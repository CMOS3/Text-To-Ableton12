---
name: ableton-mcp
description: Manages the TCP socket communication and control protocol for Ableton Live via the ahujasid/ableton-mcp server. Use this when the user requests to connect to Live, send MIDI data, or control track parameters.
---

# Ableton MCP Interaction Skill

## Goal
Establish and maintain a stable, secure bridge between the Python backend and Ableton Live using the Model Context Protocol (MCP) over a local TCP connection.

## Technical Specifications
- **Host:** 127.0.0.1 (Strict Localhost)
- **Port:** 9877
- **Protocol:** TCP/IP using JSON-encoded payloads.
- **Backend Architecture:** A uvicorn/FastAPI server (`backend/main.py`) running on `127.0.0.1:8000` exposing REST endpoints and wrapping the `GeminiAbletonClient`. The frontend is a secure Electron desktop application (`frontend/`) that communicates via NDJSON streaming for real-time status updates.
- **Remote Script Path:** D:\Sync\00 PC Sharing\Ableton\User Library\Remote Scripts

## Core Toolset Capabilities
The integration now actively supports and exposes the following full suite of capabilities to the Gemini model and the frontend interface:
- **Session & Transport:** `get_session_info`, `set_tempo`, `start_playback`, `stop_playback`.
- **Track Management:** `get_track_info`, `create_midi_track`, `set_track_name`, `select_track`, `arm_track`, `delete_track`.
- **Clip Operations:** `create_clip`, `set_clip_name`, `fire_clip`, `stop_clip`, `delete_clip`, `inject_midi_to_new_clip`.
- **Advanced MIDI Editing:** `add_notes_to_clip`, `get_notes_from_clip`, `delete_notes_from_clip`.
  - **Note Format:** Uses semantic `pitch_name` strings (e.g., "C3", "Eb2", "G#4").
  - **STRICTLY In Beats:** All `start_time` and `duration` values MUST be in beats (e.g., 4.0 = one bar in 4/4). Use floats for precision (0.25 = sixteenth note).
- **Mixing & Device Parameters:** `get_track_devices`, `get_device_parameters`, `set_device_parameter`, `design_sound`.
  - **Parameter Matching:** Uses fuzzy **string names** (e.g., "Cutoff", "Freq"). This is synonym-aware: "cutoff" will match "Filter Freq", and "gain" will match "Level".
  - **Normalization:** You MUST provide parameter values as floats strictly between **0.0 and 1.0**. The system scales these to the native device range.


## Compound Tools (Highest Priority)
**CRITICAL RULE:** You MUST prioritize Compound Tools over atomic tools.
- `get_session_mix_status`: Summary of volume/gain for all tracks.
- `set_track_volume_by_name`: Vol control by name.
- `load_device_to_track_by_name`: Load devices on named tracks.
- `inject_midi_to_new_clip`: One-step clip creation and population.

## Intelligent Routing & Context (Pure Cloud Single-Shot Compiler)
- **Cloud Orchestrator:** The system uses `gemini-3.1-pro-preview-customtools` via the `google-genai` SDK as the primary agent.
- **Global Context Pre-fetching:** Before generation, the backend locally fetches the full `session_info` (including tempo, scale, root note, and tracks) and injects it into the prompt.
- **Single-Shot Compiler:** The model evaluates the state and user prompt, outputting exactly ONE JSON array containing a sequential script of actions.
- **Sequential Execution:** The Python backend iteratively executes the JSON script with built-in async delays to prevent Ableton race conditions.


## Implementation Logic
When this skill is activated, the agent must follow these steps:

1. **0-Based Indexing Rule:** ALWAYS use 0-based integers for track and device indices.
   - User says "Track 1" -> `track_index: 0`.
   - User says "Device 2" -> `device_index: 1`.
2. **Schema Validation:** Use strictly defined Pydantic models (in `backend/schema.py`) to validate data BEFORE dispatching.
3. **Payload Structure:** All messages must be formatted as JSON on the TCP socket.
4. **Execution & Extraction:**
   - Always wrap synchronous proxy calls in `asyncio.to_thread`.
   - Use the centralized extraction pattern: Detect `status != "success"` at the proxy level and extract `data["result"]`.


## Constraints
- Do not attempt to use MIDI ports directly; always route through the TCP bridge on port 9877.
- Ensure all background listener threads are marked as `daemon=True` so they do not prevent the IDE or the backend from closing.
- Always use `self.log_message()` instead of `print()` in the Ableton Python remote script for debugging.