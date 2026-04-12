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
- **Backend Architecture:** A uvicorn/FastAPI server (`backend/main.py`) running on `127.0.0.1:8000` exposing REST endpoints and wrapping the `GeminiAbletonClient`. The Streamlit frontend (`app.py`) is strictly an HTTP client mimicking an Electron-style UI.
- **Remote Script Path:** D:\Sync\00 PC Sharing\Ableton\User Library\Remote Scripts

## Core Toolset Capabilities
The integration now actively supports and exposes the following full suite of capabilities to the Gemini model and the frontend interface:
- **Session & Transport:** `get_session_info`, `set_tempo`, `start_playback`, `stop_playback`.
- **Track Management:** `get_track_info`, `create_midi_track`, `set_track_name`, `select_track`, `arm_track`, `delete_track`.
- **Clip Operations:** `create_clip`, `set_clip_name`, `fire_clip`, `stop_clip`, `delete_clip`.
- **Advanced MIDI Editing:** `add_notes_to_clip`, `get_notes_from_clip`, `delete_notes_from_clip` (requires matching both pitch and start_time).
- **Browser & Loading:** `get_browser_tree`, `get_browser_items_at_path`, `load_instrument_or_effect`, `load_drum_kit`.
- **Mixing & Device Parameters:** `get_device_parameters`, `set_device_parameters`. *(Note: The LLM MUST always call `get_device_parameters` first to discover the numeric parameter_index before attempting to `set_device_parameters`!)*

## Implementation Logic
When this skill is activated, the agent must follow these steps for any communication attempt:

1. **Safety Check:** Ensure the destination IP is strictly `127.0.0.1`. Never attempt to bind to `0.0.0.0` or any external interface.
2. **Schema Validation:** Use strictly defined Pydantic models (in `backend/schema.py`) to validate complex JSON payloads like MIDI notes, validating data BEFORE dispatching it to the proxy.
3. **Payload Structure:** All messages must be formatted as JSON on the TCP socket.
   - Example Ping: `{"method": "ping", "params": {}}`
4. **Connection Handling:**
   - Use a non-blocking socket approach or a short timeout (2.0 seconds) initially, removing the timeout for persistent connections to prevent the application from hanging.
   - Gracefully handle `ConnectionRefusedError` and any JSON decoding errors from the Ableton side, ensuring errors propagate safely across the HTTP boundary to the UI.

## Constraints
- Do not attempt to use MIDI ports directly; always route through the TCP bridge on port 9877.
- Ensure all background listener threads are marked as `daemon=True` so they do not prevent the IDE or the backend from closing.
- Always use `self.log_message()` instead of `print()` in the Ableton Python remote script for debugging.