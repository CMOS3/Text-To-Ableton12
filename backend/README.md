# Ableton MCP Backend 🖥️

This directory contains the Python-based backend for the Text-to-Ableton project.

## Core Responsibilities
- **FastAPI Server**: Provides a REST API for the frontend and AI clients.
- **Gemini AI Client**: Integrates with Google's Generative AI (`google-genai`) to interpret musical intent and call tools.
- **MCP Proxy**: Orchestrates the communication between the AI and the Ableton Remote Script via JSON-RPC over TCP.
- **Sound Design Compiler**: Leverages specialized model instructions to autonomously design native Ableton instrument and effect chains.


## Technical Details
- **Port**: Binds to `127.0.0.1:8000`.
- **Pure Cloud Orchestration**: Employs a Single-Shot Compiler architecture using `gemini-3.1-pro-preview-customtools` via the google-genai SDK.
- **Single-Shot Execution Chain**:
    1. **Pre-fetching**: Retrieves global project context (tempo, scale, tracks) locally.
    2. **Compilation**: The model evaluates the prompt against minified JSON schemas and outputs a single JSON array of actions.
    3. **Action Preview (Dry-Run)**: The backend optionally intercepts execution, passing the plan to the frontend for user approval.
    4. **Sequential Execution**: Parses the array and executes tools sequentially with `asyncio.sleep` to prevent Ableton race conditions.
- **Async Execution**: Employs `asyncio.to_thread` for socket communication to prevent blocking the main event loop.

- **Centralized Proxy Logic**: Uses a unified `_execute_proxy_request` helper for data extraction and error handling.

## Primary Files
- `main.py`: FastAPI entry point for the Electron shell.
- `gemini_client.py`: Core logic for intent routing, semantic filtering, and tool implementation.
- `session_manager.py`: File-based CRUD interface for persisting session context, chat histories, and token metrics.
- `mcp_proxy.py`: Persistent TCP socket manager for the Ableton bridge.
- **Validation Layers**:
    - `schema.py`: Pydantic models serving as strict guardrails for all AI tool payloads.
    - `test_gemini_client.py`: Comprehensive validation suite ensuring routing, filtering, and 0-indexed track logic remain robust.

For setup instructions, please refer to the [root README](../README.md).
