# Text-to-Ableton Frontend 🎨

This directory contains the Electron-based GUI for the Text-to-Ableton project.

## Core Responsibilities
- **Desktop Shell**: Provides a secure, dedicated window for interacting with Ableton via AI.
- **User Interface**: HTML/JS/CSS-based dashboard for chat and direct control.
- **IPC Bridge**: Securely communicates between the renderer and main process via `preload.js`.

## Technical Details
- **Architecture**: Electron (Main + Renderer).
- **Styling**: Modern dark-themed CSS with glassmorphism effects.
- **Connection**: Communicates with the backend at `http://127.0.0.1:8000`.

For installation and startup instructions, please refer to the [root README](../README.md).
