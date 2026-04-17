# Ableton Remote Script (TextToAbleton) 🎹

This directory contains the custom Ableton Live Remote Script that enables external control via TCP.

## Core Responsibilities
- **TCP Listener**: Binds to `127.0.0.1:9877` inside Ableton's process.
- **JSON-RPC Server**: Interprets incoming commands and executes them using the Ableton Live Python API.
- **Thread Safety**: Uses a task queue and the `update_display` callback to ensure all Ableton API calls happen on the main thread.

## Installation
**Automatic Deployment (Windows):** Run the `deploy.ps1` PowerShell script in this directory to automatically deploy the files.

**Manual Deployment:**
1. Copy this folder to your Ableton User Library:
   `...\Documents\Ableton\User Library\Remote Scripts\TextToAbleton`
2. Restart Ableton Live.
3. Enable "TextToAbleton" as a Control Surface in Preferences.

Detailed usage and setup are covered in the [root README](../README.md).
