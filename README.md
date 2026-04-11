# Text-to-Ableton

Desktop application for controlling Ableton Live via Gemini AI.

## Architecture

- **Backend**: Python (FastAPI) - Handles Gemini API logic and MCP protocol.
- **Frontend**: Electron (Node.js) - Graphical User Interface.
- **Ableton Integration**: Python Remote Script - TCP listener on port 9877.

## Setup & Startup

### 1. Prerequisites
- Python 3.10+
- Node.js & npm
- `uv` package manager (installed via `python -m pip install uv`)

### 2. Backend Setup
1. Navigate to the `backend/` directory.
2. The environment is managed by `uv`.
3. Start the server:
   ```bash
   uv run uvicorn main:app --reload
   ```

### 3. Frontend Setup
1. Navigate to the `frontend/` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start Electron:
   ```bash
   npm start
   ```

### 4. Ableton Setup
Place the `remote_script/` folder in:
`D:\Sync\00 PC Sharing\Ableton\User Library\Remote Scripts`
Restart Ableton Live and select the script in Link/Tempo/MIDI preferences.

## Security
API keys should be placed in the root `.env` file under `GEMINI_API_KEY`.
The MCP server binds only to `127.0.0.1` for safety.
