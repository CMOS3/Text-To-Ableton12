# Text-to-Ableton 🎹

A powerful desktop application for controlling Ableton Live using Gemini AI and the Model Context Protocol (MCP).

## 🏗️ Architecture
- **Asymmetric Planner-Retriever-Executor (PRE)**: A dual-agent architecture separating reasoning from semantic mapping to minimize token cost and eliminate hallucinations.
    - **CreativePlannerAgent (Gemini 3.1 Pro)**: The main orchestrator. Acts as a "Single-Shot Compiler", taking the Ableton session state and outputting a sequential JSON array of execution actions.
    - **RetrieverAgent (Gemini 3.1 Flash-Lite)**: The semantic RAG engine. Intercepts search queries from the Planner and rapidly scans a localized `device_catalog.json` to return exact Ableton parameter names and bounds based on musical intent.
- **Backend**: Python (FastAPI) - Pre-fetches local session state, manages the multi-turn ReAct compilation loop, and sequentially executes the tool calls over the JSON-RPC proxy with async delays to mitigate race conditions.
- **Frontend**: Electron (Node.js) - Real-time NDJSON status streaming showing the orchestrator's compilation and execution steps.
- **Ableton Integration**: Custom Python Remote Script - Stable TCP-to-LOM bridge on 127.0.0.1:9877, natively mutating the Live Object Model (LOM).


## 🚀 Quick Start (Windows)

The simplest way to start both the backend and frontend simultaneously:

1. Ensure **Ableton Live** is running with the `TextToAbleton` Remote Script active.
2. Double-click **`start_app.bat`** in the root folder.

This will automatically activate the virtual environment, start the FastAPI server, and launch the Electron desktop app.

## 🛠️ Manual Setup

### 1. Prerequisites
- **Python 3.10+** (with a `.venv` in the root)
- **Node.js & npm**
- **Ableton Live 11/12**

### 2. Ableton Configuration
**Automatic Deployment (Windows):** Run the `remote_script/deploy.ps1` PowerShell script to automatically copy the Remote Script to your Ableton User Library.

**Manual Deployment:** Copy the contents of the `remote_script/` directory to your Ableton User Library:
`...\Documents\Ableton\User Library\Remote Scripts\TextToAbleton`

Select **TextToAbleton** as a Control Surface in Ableton's Link/Tempo/MIDI preferences.

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_api_key_here
```

### 4. Component Details
- **Backend**: Runs on `http://127.0.0.1:8000`. 
- **Frontend**: Electron app located in `frontend/`.


## ✨ Advanced Features

- **Multi-Turn RAG Execution**: The backend pauses the compilation loop when the Planner needs parameter data, delegating the search to the RetrieverAgent, and dynamically feeding the exact parameter constraints back into the context window.
- **Single-Shot Cloud Compiler**: High-performance orchestration powered by Gemini 3.1 Pro, enabling robust multi-step actions without infinite looping.
- **Action Preview (Dry-Run Mode)**: An optional interception gate that pauses the execution loop, presents the user with a compiled script of actions (collapsible Ableton 12-styled card), and waits for explicit approval before altering the Live set.
- **Global Project Awareness**: Automatically fetches session tempo, scale, root note, and track details *before* generation, giving the AI complete context.
- **Sequential Execution Engine**: The backend locally parses the compiled JSON script and safely executes it against Ableton with built-in race-condition protections.
- **Session Inspector UI**: Real-time display of BPM, Key, and Track count within the desktop interface.
- **Anthracite UI & UX Polish**: Premium dark theme inspired by Ableton Live 12, featuring an auto-expanding multiline chat input, a backend log drawer, and full Markdown-parsed chat responses.
- **STRICT Beat-Based Timing**: Orchestral-grade precision where all MIDI lengths and start times are handled in beats (e.g., 4 bars = 16.0 beats in 4/4).
- **Compound Tools (Optimized)**: High-priority macros (`get_session_mix_status`, `inject_midi_to_new_clip`) that parse track states and inject data in bulk.
- **NDJSON Streaming**: Real-time feedback window showing granular agent status (Compiling -> Executing -> Finished).
