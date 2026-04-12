# Ableton MCP Backend 🖥️

This directory contains the Python-based backend for the Text-to-Ableton project.

## Core Responsibilities
- **FastAPI Server**: Provides a REST API for the frontend and AI clients.
- **Gemini AI Client**: Integrates with Google's Generative AI (`google-genai`) to interpret musical intent and call tools.
- **MCP Proxy**: Orchestrates the communication between the AI and the Ableton Remote Script via JSON-RPC over TCP.

## Technical Details
- **Port**: Binds to `127.0.0.1:8000`.
- **Primary Files**:
    - `main.py`: API entry point and routes.
    - `gemini_client.py`: Logic for tool calling and AI personality.
    - `mcp_proxy.py`: Low-level TCP connection management to Ableton.

For setup instructions, please refer to the [root README](../README.md).
