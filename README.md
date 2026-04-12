# Text-to-Ableton 🎹

A powerful desktop application for controlling Ableton Live using Gemini AI 1.5 and the Model Context Protocol (MCP).

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
Copy the contents of the `remote_script/` directory to your Ableton User Library:
`...\Documents\Ableton\User Library\Remote Scripts\TextToAbleton`

Select **TextToAbleton** as a Control Surface in Ableton's Link/Tempo/MIDI preferences.

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_api_key_here
```

### 4. Component Details
- **Backend**: Runs on `http://127.0.0.1:8000`. API documentation available at `/docs` when running.
- **Frontend**: Electron app located in `frontend/`. Use `npm install` inside the folder before first run.

## 🔒 Security
- The backend binds to `127.0.0.1` by default to prevent unauthorized external access.
- API keys are managed via environment variables and should never be committed to version control.

## ✨ Advanced Features
- **Intelligent Intent Router**: Automatically selects the most efficient model. Simple commands use `Gemini 3.1 Flash-Lite` ($0.00/mill), while complex composition tasks use `Gemini 3.1 Pro`.
- **Context Memory**: Remembers past interactions within a session, allowing for conversational multi-step MIDI editing.
- **Real-time Cost tracking**: Live dashboard showing token usage and estimated USD cost for both models.
- **Macro Manager**: Save frequently used prompts as custom buttons for one-click execution.
- **Genre Context**: Persistent style setting that automatically prepends context to your prompts.

---
*Maintained at: https://github.com/CMOS3/Text-To-Ableton12*
