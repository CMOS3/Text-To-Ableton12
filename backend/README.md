# Ableton MCP Backend 🖥️

This directory contains the Python-based backend for the Text-to-Ableton project.

## Core Responsibilities
- **FastAPI Server**: Provides a REST API for the frontend and AI clients.
- **Gemini AI Client**: Integrates with Google's Generative AI (`google-genai`) to interpret musical intent and call tools.
- **MCP Proxy**: Orchestrates the communication between the AI and the Ableton Remote Script via JSON-RPC over TCP.
- **Sound Design Sub-Agent**: Leverages specialized model instructions to autonomously design native Ableton instrument and effect chains.


## Technical Details
- **Port**: Binds to `127.0.0.1:8000`.
- **Hybrid AI Execution Chain**:
    1. **Local Interception (Ollama)**: Pings `http://127.0.0.1:11434` with `gemma4:e4b` to handle transport fast-paths.
    2. **Semantic Filtering (Cloud Flash)**: Uses Gemini 3 Flash to reduce the toolset to only the strictly necessary schemas.
    3. **Agentic Reasoning (Cloud Pro)**: Executes complex musical logic using Gemini 3.1 Pro via an async loop.
- **Async Execution**: Employs `asyncio.to_thread` for tool calls to prevent blocking the main event loop.
- **Centralized Proxy Logic**: Uses a unified `_execute_proxy_request` helper for data extraction and error handling.

## Primary Files
- `main.py`: FastAPI entry point for the Electron shell.
- `gemini_client.py`: Core logic for intent routing, semantic filtering, and tool implementation.
- `mcp_proxy.py`: Persistent TCP socket manager for the Ableton bridge.
- **Validation Layers**:
    - `schema.py`: Pydantic models serving as strict guardrails for all AI tool payloads.
    - `test_gemini_client.py`: Comprehensive validation suite ensuring routing, filtering, and 0-indexed track logic remain robust.

For setup instructions, please refer to the [root README](../README.md).
