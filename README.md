# Text-to-Ableton 🎹

A powerful desktop application for controlling Ableton Live using Gemini AI and the Model Context Protocol (MCP).

## 🏗️ Architecture

- **Hybrid AI Pipeline**: A multi-tiered orchestration layer:
    - **Local Router**: Ollama (`gemma4:e4b`) intercepts atomic transport/playback commands for zero-latency execution.
    - **Semantic Filter**: Gemini 3 Flash analyzes complex prompts to pick only the necessary tool schemas, preventing token bloat.
    - **Cloud Execution**: Gemini 3.1 Pro handles deep musical reasoning and multi-step composition.
- **Backend**: Python (FastAPI) - Manages the model chains and serves as the JSON-RPC proxy.
- **Frontend**: Electron (Node.js) - "Anthracite UI" with real-time NDJSON status streaming.
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
- **Ollama** (Optional, for local routing)

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
- **Ollama**: Ensures `gemma4:e4b` is pulled locally for fast-path transport commands.


## ✨ Advanced Features

- **Autonomous Sound Design**: A specialized sub-agent that manipulates native Ableton device parameters based on creative descriptions (e.g., "Give me a gritty, dark warehouse bass").
- **Hybrid Intelligence**: Combines local open-weight models for speed/cost with cloud-scale reasoning for creativity.

- **Semantic Tool Filtering**: Dynamically builds the LLM's function list based on intent, keeping context windows lean.
- **STRICT Beat-Based Timing**: Orchestral-grade precision where all MIDI lengths and start times are handled in beats (e.g., 4 bars = 16.0 beats in 4/4).
- **Compound Tools (Optimized)**: High-priority macros (`get_session_mix_status`, `generate_named_midi_pattern`) that parse volume, panning, and track states in bulk.
- **NDJSON Streaming**: Real-time feedback window showing granular agent status (Thinking -> Filtering -> Calling -> Analyzing).
- **Robust Error Propagation**: Centralized handler enables the AI to self-correct based on specific Ableton API feedback.
- **Anthracite UI**: Premium dark theme inspired by Ableton Live 12 with glassmorphic elements.


---
*Maintained at: https://github.com/CMOS3/Text-To-Ableton12*
