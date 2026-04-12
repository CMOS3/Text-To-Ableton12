# Text-to-Ableton Frontend 🎨

This directory contains the Electron-based GUI for the Text-to-Ableton project.

## Core Responsibilities
- **Desktop Shell**: Provides a secure, dedicated window for interacting with Ableton via AI.
- **User Interface**: HTML/JS/CSS-based dashboard for chat and direct control.
- **IPC Bridge**: Securely communicates between the renderer and main process via `preload.js`.

## Technical Details
- **Architecture**: Electron (Main + Renderer).
- **Styling**: "Anthracite" dark-themed CSS with glassmorphism, inspired by Ableton Live 12.
- **Connection**: Communicates with the FastAPI backend using NDJSON streaming for real-time agentic status updates.

## Development
```bash
npm install
npm start
```
*Note: Ensure the backend is running first for full functionality.*

For installation and startup instructions, please refer to the [root README](../README.md).
