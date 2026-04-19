# AbletonMCP with Gemini API - Current Architecture

Based on the actual codebase, here is the detailed architecture of the system as it currently functions. 

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
  * **Schema Definition (`schema.py`)**: Uses Pydantic to strictly define the input models/schemas for any tool calls. These schemas are programmatically converted into native JSON-schema tool definitions for the orchestrator.

### The AI Orchestrator (`gemini_client.py`)
Despite retaining the `GeminiAbletonClient` name, the codebase has recently undergone a major migration:
* **Local Ollama Orchestrator Loop**: The primary agentic loop actually runs against a localized Ollama instance querying the `VladimirGav/gemma4-26b-16GB-VRAM` model via `httpx`.
* **Tool Calling Loop**: Parses Ollama's tool requests, sequentially calls internal proxy methods, appends results (handling stringified dict formatting), and loops back to Ollama.
* **Circuit Breaker**: A strict `MAX_ITERATIONS = 5` limit prevents infinite tool looping and memory overflow.
* **Cloud Expert Bypass**: It exposes one specialized Cloud Tool (`consult_cloud_expert`) which routes an API request to the *actual* Google Gemini API (`models/gemini-3.1-pro-preview-customtools`). If the model invokes this tool, the Python loop physically hard-stops, returning the text directly to the user to enforce a "passive expert" paradigm and stop further looping.

---

## 3. Ableton Live Remote Script
*Location: `remote_script/`*

A Python module loaded directly deep inside Ableton Live, acting as a headless control surface.

* **Tech Stack**: Ableton's `_Framework.ControlSurface`, native Python `socket`, `threading`, and `queue`.
* **Key Components**:
  * **TCP Server Listener (`__init__.py`)**: Binds a socket to `127.0.0.1:9877` on a daemon thread, accepting incoming connections and commands from the MCP Proxy.
  * **Thread-Safe Task Queue**: Uses the `update_display` system tick inside Ableton to safely pop off the thread-safe `task_queue`, ensuring that external TCP requests interact safely with Ableton's primary UI thread (`execute_safely`).
  * **Command Dispatcher**: Translates JSON method names (e.g., `set_tempo`, `get_browser_tree`, `inject_midi_to_new_clip`) into direct interactions with the `.song()`, `.application().browser`, and `.tracks` internal Ableton Python APIs.

---

## Data Flow Pipeline

1. **User Request**: User sends a chat message via standard UI.
2. **Backend Entry**: `main.py` gets `POST /chat`, invokes `gemini_client.chat()`.
3. **Orchestrator Eval**: `gemini_client` sends history and available JSON-schema Tools to Local Ollama via `POST http://127.0.0.1:11434/api/chat`.
4. **Tool Execution**: Ollama returns `tool_calls`. `gemini_client` matches the name, invokes the function (e.g., `set_tempo`).
5. **Proxy Request**: The proxy formats a payload `{"method": "set_tempo", params: {"tempo": 120.0}}` and blasts it over TCP port 9877.
6. **Ableton Execution**: The remote script listener parses it on the background thread, queues it. When Ableton ticks, the main thread pops it, sets `self.song().tempo = 120.0`, and sends `{"result": "ok"}` back over the socket.
7. **Resolution**: AI Orchestrator receives the proxy value, feeds it back into Ollama, and eventually streams the final response (`application/x-ndjson`) back to the frontend UI renderer.
