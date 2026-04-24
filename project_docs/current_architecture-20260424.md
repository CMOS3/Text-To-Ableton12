# AbletonMCP with Gemini API - Current Architecture (As of 2026-04-24)

Based on the actual codebase, here is the detailed architecture of the system as it currently functions, specifically reflecting the recent refactoring to a "Single-Shot Compiler" pattern.

## System Overview

The system bridges a Large Language Model orchestrator with Ableton Live, allowing users to control their Ableton session, design sounds, and arrange clips through natural language. It comprises three major decoupled components: 
1. **Frontend (Electron/Web UI)**
2. **Backend (FastAPI Server + AI Orchestrator)**
3. **Ableton Live Remote Script (TCP Server)**

---

## 1. Frontend (User Interface)
*Location: `frontend/`*

An Electron-based web application providing a chat-like interface.

* **Tech Stack**: Vanilla HTML/JS/CSS wrapper in Electron (`index.html`, `renderer.js`, `main.js`, `preload.js`).
* **Responsibilities**:
  * Captures user input and displays AI responses.
  * Streams LLM responses chunk-by-chunk using NDJSON (`application/x-ndjson`).
  * Manages settings like Backend URL, Macro definitions, and model cost/token tracking.
  * Connects to the backend via HTTP (`POST http://127.0.0.1:8000/chat`).

---

## 2. Backend (FastAPI Server & AI Orchestration layer)
*Location: `backend/`*

This is the central nervous system connecting the frontend to the language models and Ableton.

* **Tech Stack**: Python, FastAPI, Uvicorn, Pydantic, HTTPX, Google GenAI SDK.
* **Key Components**:
  * **Main API (`main.py`)**: A FastAPI app exposing the `/chat` endpoint for the frontend, as well as several raw `/api/*` endpoints meant for direct functional testing.
  * **MCP Proxy (`mcp_proxy.py`)**: A lightweight Python TCP client (`127.0.0.1:9877`) that sends commands to Ableton Live using a JSON-RPC 2.0-style format (`method`, `params`). It handles retries, timeouts, and JSON parsing.
  * **Schema Definition (`schema.py`)**: Uses Pydantic to strictly define the input models/schemas for any tool calls. These schemas are programmatically flattened into a minified JSON-schema representation to inject into the system prompt.

### The AI Orchestrator (`gemini_client.py`)
The orchestrator leverages a **Pure Cloud Single-Shot Compiler** architecture via the `google-genai` SDK:
* **Single-Shot Compiler Pattern**: Instead of a multi-turn tool-calling loop, the system now runs a single-shot generation against `models/gemini-3.1-pro-preview-customtools`. 
* **Global Context Pre-fetching**: Before calling the LLM, the backend makes a local call to `get_session_info` (which includes track states, tempo, and scale info) to gather the full project state. This local state is appended directly to the user's prompt.
* **Strict JSON Array Output**: The Google SDK's native function calling is explicitly disabled (`automatic_function_calling=disable`). Instead, the system prompt contains minified JSON schemas for over 30 available tools, and the LLM is instructed to output exactly ONE valid JSON array representing a sequential script of actions.
* **Sequential Local Execution**: After generating the JSON array, the backend parses it and iterates over the actions. It sequentially calls internal proxy methods corresponding to the tools, implementing intentional async delays (`asyncio.sleep(0.5)`) between calls to mitigate race conditions in the Ableton queue.

---

## 3. Ableton Live Remote Script
*Location: `remote_script/`*

A Python module loaded directly deep inside Ableton Live, acting as a headless control surface.

* **Tech Stack**: Ableton's `_Framework.ControlSurface`, native Python `socket`, `threading`, and `queue`.
* **Key Components**:
  * **TCP Server Listener (`__init__.py`)**: Binds a socket to `127.0.0.1:9877` on a daemon thread, accepting incoming connections and commands from the MCP Proxy.
  * **Thread-Safe Task Queue**: Uses the `update_display` system tick inside Ableton to safely pop off the thread-safe `task_queue`, ensuring that external TCP requests interact safely with Ableton's primary UI thread (`execute_safely`).
  * **Command Dispatcher**: Translates JSON method names (e.g., `set_tempo`, `get_browser_tree`, `inject_midi_to_new_clip`) into direct interactions with the `.song()`, `.application().browser`, and `.tracks` internal Ableton Python APIs. It also provides global session awareness such as Scale Mode, Root Note, and Tempo.

---

## Data Flow Pipeline

1. **User Request**: User sends a chat message via standard UI.
2. **Backend Entry**: `main.py` gets `POST /chat`, invokes `gemini_client.chat()`.
3. **State Pre-fetch**: The orchestrator pauses to fetch the current Ableton state (`get_session_info`).
4. **LLM Generation**: The system sends the prompt, history, injected session state, and minified tool schemas to `gemini-3.1-pro-preview-customtools`.
5. **Script Compilation**: The LLM generates a single JSON array of tool actions (e.g., `[{"tool": "create_midi_track", "args": {"track_name": "Drums"}}, ...]`).
6. **Sequential Execution**: The orchestrator loops over the JSON array. For each action, it formats a payload `{"method": "create_midi_track", "params": {"track_name": "Drums"}}` and sends it over TCP port 9877.
7. **Ableton Execution**: The remote script listener receives the command on the background thread, queues it. When Ableton ticks, the main thread executes it (`self.song().create_midi_track(-1)`) and sends an acknowledgment back over the socket.
8. **Resolution**: The backend delays briefly to prevent race conditions, executes the next tool in the JSON array, and ultimately streams the final execution results back to the frontend UI renderer via NDJSON.
