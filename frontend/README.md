# Text-to-Ableton Frontend 🎨

This directory contains the Electron-based GUI for the Text-to-Ableton project.

## Core Responsibilities
- **Desktop Shell**: Provides a secure, dedicated window for interacting with Ableton via AI.
- **User Interface**: HTML/JS/CSS-based dashboard for chat and direct control.
- **IPC Bridge**: Securely communicates between the renderer and main process via `preload.js`.

## Technical Details
- **Architecture**: Electron (Main + Renderer).
- **Styling**: "Anthracite" neutral dark-themed CSS inspired by Ableton Live 12, featuring a dynamic flex layout.
- **Connection**: Communicates with the FastAPI backend using NDJSON streaming for real-time agentic status updates.
- **Features**:
  - **Session Drawer**: A dedicated slide-out drawer consolidating live stats (BPM, Key, Tracks), session controls, and hierarchical per-prompt token cost tracking.
  - **Responsive Chat Panel**: The main chat window dynamically squeezes when the drawer is open to prevent text overlap.
  - **Action Preview**: An interception UI that morphs a confirmation card into a collapsible execution trace, allowing users to approve/cancel AI scripts before execution.
  - **Markdown & Code Rendering**: Chat relies on `marked.js` to render formatted responses.
  - **Backend Log Drawer**: Built-in drawer to observe raw Python stdout/stderr in real time.

## Development
```bash
npm install
npm start
```
*Note: Ensure the backend is running first for full functionality.*

For installation and startup instructions, please refer to the [root README](../README.md).
