# Text-to-Ableton 🎹

A powerful desktop application for controlling Ableton Live using Gemini AI and the Model Context Protocol (MCP).

## 🏗️ Architecture

- **Pure Cloud Orchestration**: The primary agentic loop runs entirely via Google's `gemini-3.1-flash-lite`.
    - **Native Tool Calling**: The model autonomously selects and executes tools in an iterative loop (max 5 iterations).
    - **Zero Local Overhead**: Frees up all local VRAM by pushing routing to the cloud.
- **Cloud Expert Bypass**: A specialized tool (`consult_cloud_expert`) provides a textual bridge to **Gemini 3.1 Pro**. This expert is used for complex music theory advice and sound design guidance without further tool looping.
- **Backend**: Python (FastAPI) - Manages the iterative tool loop, model telemetry, and the JSON-RPC proxy.
- **Frontend**: Electron (Node.js) - Real-time NDJSON status streaming showing the orchestrator's thoughts.
- **Ableton Integration**: Custom Python Remote Script - Stable TCP-to-LOM bridge on 127.0.0.1:9877.


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

- **Cloud Orchestrator**: High-performance tool calling powered by Gemini 3.1 Flash-Lite, preventing context dilution.
- **Cloud Production Expert**: Direct access to Google’s most powerful model for musical creative consulting.
- **Iterative Reasoning**: A stateful loop that allows the orchestrator to check state, make a change, and verify results autonomously.
- **STRICT Beat-Based Timing**: Orchestral-grade precision where all MIDI lengths and start times are handled in beats (e.g., 4 bars = 16.0 beats in 4/4).
- **Compound Tools (Optimized)**: High-priority macros (`get_session_mix_status`, `generate_named_midi_pattern`) that parse volume, panning, and track states in bulk.
- **NDJSON Streaming**: Real-time feedback window showing granular agent status (Thinking -> Executing -> Analyzing).
- **Anthracite UI**: Premium dark theme inspired by Ableton Live 12 with glassmorphic elements.


---
*Maintained at: https://github.com/CMOS3/Text-To-Ableton12*
