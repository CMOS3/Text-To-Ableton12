# Ableton MCP Backend 🖥️

This directory contains the Python-based backend for the Text-to-Ableton project.

## Core Responsibilities
- **FastAPI Server**: Provides a REST API for the frontend and AI clients.
- **Gemini AI Client**: Integrates with Google's Generative AI (`google-genai`) to interpret musical intent and call tools.
- **MCP Proxy**: Orchestrates the communication between the AI and the Ableton Remote Script via JSON-RPC over TCP.

## Technical Details
- **Port**: Binds to `127.0.0.1:8000`.
- **Async Execution**: Employs `asyncio.to_thread` for tool calls to prevent blocking the main event loop during TCP/IP communication with Ableton.
- **Centralized Proxy Logic**: Uses a unified `_execute_proxy_request` helper to handle JSON-RPC handshakes, error propagation, and automatic result extraction.

## Primary Files
- `main.py`: FastAPI entry point, exposing REST endpoints for the Electron shell.
- `gemini_client.py`: Core agentic loop, intent routing, and tool implementation.
- `mcp_proxy.py`: Persistent TCP socket manager handling the JSON protocol bridge to Ableton.
- `schema.py`: Pydantic models ensuring type-safe communication between all layers.

For setup instructions, please refer to the [root README](../README.md).
