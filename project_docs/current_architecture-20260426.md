# AbletonMCP with Gemini API - Current Architecture (As of 2026-04-26)

Based on the actual codebase, here is the detailed architecture of the system as it currently functions, specifically reflecting the recent enhancements in prompt-engineering, compound tooling, and fuzzy-matching algorithms built upon the "Single-Shot Compiler" pattern.

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
* **Key Features**:
  * **Anthracite Theme**: Ableton 12 inspired glassmorphic dark theme.
  * **Session Inspector**: Real-time display of Ableton BPM, Key, and Track count.
  * **Backend Log Drawer**: Integrated viewer for Python backend logs.
  * **Execution Trace Indicator**: A collapsible UI element showing "Thinking/Execution Trace" status to provide transparency during the LLM compilation phase.
  * **Cost Tracking & Optimization**: Dynamic calculation of tokens and monetary cost separated by Gemini model variants (Flash vs. Pro).
  * **Markdown Chat**: Responses parsed and rendered as Markdown with `marked.js`.
* **Responsibilities**:
  * Captures user input (via auto-expanding multiline textarea) and displays AI responses.
  * Streams LLM responses chunk-by-chunk using NDJSON (`application/x-ndjson`).
  * Manages settings like Backend URL, Action Preview toggle, and model cost/token tracking.
  * Connects to the backend via HTTP (`POST http://127.0.0.1:8000/chat`).
  * Intercepts `approval_required` chunks to render a collapsible confirmation card, letting the user manually approve or cancel the pending action script (Dry Run Mode).

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
* **Global Context Pre-fetching**: Before calling the LLM, the backend makes a local call to `get_session_info` (which includes track states, tempo, and scale info) to gather the full project state. This local state is appended directly to the user's prompt. *Note: Context injection logic actively prevents double-injection of user prompts when merging history.*
* **Strict JSON Array Output**: The Google SDK's native function calling is explicitly disabled (`automatic_function_calling=disable`). Instead, the system prompt contains minified JSON schemas for over 30 available tools, and the LLM is instructed to output exactly ONE valid JSON array representing a sequential script of actions.
* **Strict Persona & Formatting Enforcements**:
  * The System Prompt strictly enforces a "professional, clinical" Ableton Live technical consultant persona.
  * The LLM is mandated to format text using Markdown.
  * **Manual Actions Required:** A mandatory section where the LLM provides specific manual UI tweak instructions for device parameters that fall outside the automated scope.
* **Compound Tools Implementation**: 
  * `sound_design`: A highly guarded macro tool enforcing a "Safe Menu" of allowed devices/parameters. It expects normalized float values (0.0 to 1.0) and uses backend fuzzy matching to find tracks and devices by name.
  * `mix_track`: A composite tool allowing simultaneous adjustment of track volume, panning, and mute states.
* **Action Preview (Dry-Run Interception)**: If enabled, the generated JSON script pauses execution. The backend yields an `approval_required` NDJSON chunk to the frontend and `await`s a global `asyncio.Event`. The frontend presents a collapsible `.approval-card` and calls `POST /api/action-response` to set the event based on user input.
* **Sequential Local Execution**: After generating the JSON array (and receiving user approval), the backend parses it and iterates over the actions. It sequentially calls internal proxy methods, implementing intentional async delays (`asyncio.sleep(0.5)`) between calls to mitigate race conditions.

---

## 3. Ableton Live Remote Script
*Location: `remote_script/`*

A Python module loaded directly deep inside Ableton Live, acting as a headless control surface.

* **Tech Stack**: Ableton's `_Framework.ControlSurface`, native Python `socket`, `threading`, and `queue`.
* **Key Components**:
  * **TCP Server Listener (`__init__.py`)**: Binds a socket to `127.0.0.1:9877` on a daemon thread, accepting incoming connections and commands from the MCP Proxy.
  * **Thread-Safe Task Queue**: Uses the `update_display` system tick inside Ableton to safely pop off the thread-safe `task_queue`, ensuring that external TCP requests interact safely with Ableton's primary UI thread (`execute_safely`).
  * **Command Dispatcher**: Translates JSON method names into direct interactions with the `.song()`, `.application().browser`, and `.tracks` internal APIs.
  * **Fuzzy-Matching Parameter Logic (`_do_set_device_parameter`)**: Features a sophisticated three-tier matching system to handle LLM hallucinations and varied user inputs:
    1. Exact alphanumeric match.
    2. Substring match.
    3. Synonym mapping (e.g., mapping "cutoff" to "filterfreq", or "volume" to "gain").
  * **Composite Mix Handler (`_do_set_track_mixer`)**: Handles safe, bounded execution of volume, panning, and mute states simultaneously on the main Ableton UI thread.

---

## Data Flow Pipeline

1. **User Request**: User sends a chat message via standard UI.
2. **Backend Entry**: `main.py` gets `POST /chat`, invokes `gemini_client.chat()`.
3. **State Pre-fetch**: The orchestrator pauses to fetch the current Ableton state (`get_session_info`) and merges it cleanly with the user prompt.
4. **LLM Generation**: The system sends the prompt, history, injected session state, and minified tool schemas to `gemini-3.1-pro-preview-customtools`.
5. **Script Compilation**: The LLM generates a single JSON array of tool actions (e.g., `[{"tool": "sound_design", "args": {"track_name": "Drums", "device_name": "Filter", "tweaks": {"Frequency": 0.5}}}]`).
6. **Action Interception (Optional)**: If Action Preview is active, the backend yields an `approval_required` NDJSON stream and halts. The user approves or cancels via the `.approval-card`.
7. **Sequential Execution**: The orchestrator loops over the JSON array. For each action, it formats a payload `{"method": "set_device_parameter", "params": {"track_index": 0, "device_index": 1, "parameter_name": "Frequency", "value": 0.5}}` and sends it over TCP port 9877.
8. **Ableton Execution**: The remote script listener receives the command on the background thread, queues it. When Ableton ticks, the main thread executes it (using fuzzy-matching if applicable) and sends an acknowledgment back over the socket.
9. **Resolution**: The backend delays briefly to prevent race conditions, executes the next tool in the JSON array, and ultimately streams the final execution results back to the frontend UI renderer via NDJSON.
