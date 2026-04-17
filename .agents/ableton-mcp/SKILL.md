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
- **Clip Operations:** `create_clip`, `set_clip_name`, `fire_clip`, `stop_clip`, `delete_clip`.
- **Advanced MIDI Editing:** `add_notes_to_clip`, `get_notes_from_clip`, `delete_notes_from_clip` (requires matching both pitch and start_time).
- **Browser & Loading:** `get_browser_tree`, `get_browser_items_at_path`, `load_instrument_or_effect`, `load_drum_kit`.
- **Mixing & Device Parameters:** `get_device_parameters`, `set_device_parameters`. *(Note: The LLM MUST always call `get_device_parameters` first to discover the numeric parameter_index before attempting to `set_device_parameters`!)*

## Compound Tools (Highest Priority)
**CRITICAL RULE:** You MUST prioritize Compound Tools over atomic tools to gather bulk data or perform multi-step operations. Do not iterate through individual tracks or perform atomic operations when a single compound tool exists.
- `get_session_mix_status`: Retrieves a summary of volume/gain status for all tracks in one go.
- `set_track_volume_by_name`: Sets the volume of a track by its name in dB.
- `load_device_to_track_by_name`: Loads a device onto a track, both specified by name.
- `generate_named_midi_pattern`: Creates a clip, names it, and populates it with MIDI notes in one step.

## Intelligent Routing & Context
- **Intent Router:** The system uses a dual-model approach. `Gemini 3.1 Flash-Lite` acts as a binary classifier to route simple direct commands (tagged `FLASH`) vs complex reasoning tasks (tagged `PRO`).
- **Context Persistence:** Every user message is prepended with a `[Style: <Genre>]` tag if a Genre is configured in the UI. 
- **Conversation Memory:** The `chat_history` is passed as an array of `genai.types.Content` objects, enabling the model to reference previous steps (e.g., "Add the same notes to the new track").
- **Token Efficiency:** The UI monitors `input_tokens` and `output_tokens` via `usage_metadata` for real-time cost-per-session analysis.

## Implementation Logic
When this skill is activated, the agent must follow these steps for any communication attempt:

1. **Safety Check:** Ensure the destination IP is strictly `127.0.0.1`. Never attempt to bind to `0.0.0.0` or any external interface.
2. **Schema Validation:** Use strictly defined Pydantic models (in `backend/schema.py`) to validate complex JSON payloads like MIDI notes, validating data BEFORE dispatching it to the proxy.
3. **Payload Structure:** All messages must be formatted as JSON on the TCP socket.
   - Example Ping: `{"method": "ping", "params": {}}`
4. **Execution & Extraction:**
   - Always wrap synchronous proxy calls in `asyncio.to_thread` when executing within the async agent loop.
   - Use the centralized extraction pattern: Detect `status != "success"` at the proxy level, then drill into `data["error"]` for Ableton-specific failures, and finally extract `data["result"]` for tool consumption.
   - Propagate clear, human-readable errors back to the LLM so it can attempt self-correction (e.g., "Clip Slot index out of range").
5. **Connection Handling:**
   - Use a persistent, thread-safe socket approach. Gracefully handle `ConnectionRefusedError` and ensure the proxy can re-establish the bridge automatically if Ableton is restarted.

## Constraints
- Do not attempt to use MIDI ports directly; always route through the TCP bridge on port 9877.
- Ensure all background listener threads are marked as `daemon=True` so they do not prevent the IDE or the backend from closing.
- Always use `self.log_message()` instead of `print()` in the Ableton Python remote script for debugging.