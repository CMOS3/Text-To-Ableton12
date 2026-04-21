# Ableton MCP Backend 🖥️

This directory contains the Python-based backend for the Text-to-Ableton project.

## Core Responsibilities
- **FastAPI Server**: Provides a REST API for the frontend and AI clients.
- **Gemini AI Client**: Integrates with Google's Generative AI (`google-genai`) to interpret musical intent and call tools.
- **MCP Proxy**: Orchestrates the communication between the AI and the Ableton Remote Script via JSON-RPC over TCP.
- **Sound Design Sub-Agent**: Leverages specialized model instructions to autonomously design native Ableton instrument and effect chains.


## Technical Details
- **Port**: Binds to `127.0.0.1:8000`.
- **Pure Cloud Orchestration**: Employs an iterative loop using `gemini-3.1-flash-lite` to autonomously execute Ableton tools via the google-genai SDK.
- **Iterative Execution Chain**:
    1. **Tool Evaluation**: Model evaluates the prompt and history against valid JSON schemas.
    2. **Execution Loop**: Executes tools (max 5 iterations) and appends results to history.
    3. **Cloud Expert Bypass**: If `consult_cloud_expert` is called, the loop halts and returns expert textual advice from Gemini 3.1 Pro.
- **Async Execution**: Employs `asyncio.to_thread` for socket communication to prevent blocking the main event loop.

- **Centralized Proxy Logic**: Uses a unified `_execute_proxy_request` helper for data extraction and error handling.

## Primary Files
- `main.py`: FastAPI entry point for the Electron shell.
- `gemini_client.py`: Core logic for intent routing, semantic filtering, and tool implementation.
- `mcp_proxy.py`: Persistent TCP socket manager for the Ableton bridge.
- **Validation Layers**:
    - `schema.py`: Pydantic models serving as strict guardrails for all AI tool payloads.
    - `test_gemini_client.py`: Comprehensive validation suite ensuring routing, filtering, and 0-indexed track logic remain robust.

For setup instructions, please refer to the [root README](../README.md).
