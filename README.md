# Text-to-Ableton 🎹

A powerful desktop application for controlling Ableton Live using Gemini AI and the Model Context Protocol (MCP).

## 🏗️ Architecture

- **Backend**: Python (FastAPI) - Orchestrates Gemini API interactions and serves as a proxy to the Ableton Remote Script.
- **Frontend**: Electron (Node.js) - A modern, responsive desktop interface.
- **Ableton Integration**: custom Python Remote Script - Implements a robust TCP-to-JSON-RPC listener within Ableton Live.

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
- **Backend**: Runs on `http://127.0.0.1:8000`. API documentation available at `/docs` when running.
- **Frontend**: Electron app located in `frontend/`. Run `npm install` inside the folder before the first run.

## 🔒 Security
- The backend binds to `127.0.0.1` by default to prevent unauthorized external access.
- API keys are managed via environment variables and should never be committed to version control.

## ✨ Advanced Features

- **Intelligent Intent Router**: Automatically selects the most efficient model. Simple commands use `Gemini 3.1 Flash-Lite`, while complex composition tasks use `Gemini 3.1 Pro`.
- **Compound Tools (Optimized)**: High-priority backend macros (e.g., `get_session_mix_status`, `generate_named_midi_pattern`) group complex multi-step operations. Now featuring centralized result extraction and detailed parsing for volume, panning, and track states.
- **NDJSON Streaming**: Real-time feedback in the UI during agentic loops, showing exactly what the AI is "thinking" or calling in Ableton with granular status updates.
- **Robust Error Propagation**: Centralized handler detects and propagates specific Ableton Live errors back to the AI, enabling intelligent self-correction for failed commands.
- **Anthracite UI**: A premium, glassmorphic dark theme inspired by Ableton Live 12, featuring custom scrollbars and interactive state feedback.
- **Token Analysis**: Live dashboard showing token usage for every interaction to monitor efficiency in real-time.
- **Macro Manager**: Save frequently used prompts as custom buttons for one-click execution.
- **Genre Context**: Persistent style setting that automatically prepends context to your prompts.

---
*Maintained at: https://github.com/CMOS3/Text-To-Ableton12*
