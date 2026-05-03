# Text-To-Ableton (TTA) Architectural Blueprint
**Date:** 2026-04-30
**State:** Asymmetric Planner-Retriever-Executor (PRE) Architecture

## 1. High-Level System Overview
The TTA application is designed to autonomously translate natural language musical intents into precise actions within an active Ableton Live 12 session. To achieve low latency, high reliability, and cost-efficiency, the system employs an asymmetric Multi-Agent Architecture consisting of a heavy reasoning engine (The Planner) and a lightweight semantic search engine (The Retriever).

The system consists of four primary domains:
1. **Frontend (Electron UI):** Captures user intent and renders conversational and executable output.
2. **Backend Orchestrator (FastAPI/Python):** Hosts the LLM execution logic, ReAct loops, and tool orchestration.
3. **MCP Proxy (Socket Server):** Bridges standard Python function calls with the Ableton Python environment.
4. **Ableton Remote Script:** The native Ableton API interface that physically mutates the Live Object Model (LOM).

---

## 2. Core Components

### 2.1 The AI Agents
The AI tier is heavily optimized to eliminate token bloat (hallucinations) and reduce API costs by delegating specific tasks to appropriately sized models.

#### **CreativePlannerAgent (Gemini 3.1 Pro)**
- **Role:** The primary reasoning engine and "Single-Shot Compiler."
- **Function:** It acts as a senior Ableton consultant. It ingests the user's intent, the session state, and the genre context, and outputs a strict JSON array of sequential proxy commands (e.g., `create_midi_track`, `load_instrument_or_effect`, `inject_midi_to_new_clip`).
- **Execution Style:** Operates in a **Pre-Execution ReAct Loop**. Before compiling its final mutation script, it can output context-gathering tools (like `fetch_resource` or `search_device_parameters`) to learn about the environment dynamically.

#### **RetrieverAgent (Gemini 3.1 Flash-Lite)**
- **Role:** The Semantic RAG Engine.
- **Function:** Solves the Ableton parameter mapping problem. Instead of forcing the expensive Pro model to memorize thousands of proprietary Ableton parameter names, the Retriever queries a localized, ground-truth catalog (`backend/device_catalog.json`).
- **Execution:** When the Planner asks for "Filter Cutoff", the Retriever semantically matches this to Ableton's exact internal string (`"Filter 1 Freq"`) and returns its strict `min`/`max` bounds.

### 2.2 The Integration Layer

#### **FastAPI Server (`backend/main.py`)**
- Exposes the `/chat` endpoint.
- Streams NDJSON (`application/x-ndjson`) back to the frontend, ensuring the user sees real-time status updates (e.g., "[STATUS] Executing 1/3: load_instrument...").

#### **MCP Proxy (`backend/mcp_proxy.py`)**
- A lightweight socket client.
- Translates the LLM's executed JSON script (like `set_track_volume(0, 0.85)`) into a serialized string sent over localhost.

#### **Ableton Remote Script (`remote_script/AbletonMCP.py`)**
- Runs inside Ableton Live 12's embedded Python 3 environment.
- Deserializes proxy strings (accounting for the custom TOON format) and natively invokes the `Live.Track`, `Live.Device`, and `Live.Clip` APIs.

### 2.3 Session Management & Persistence

#### **Backend Storage (`backend/session_manager.py`)**
- Implements isolated, file-based JSON persistence in `backend/data/sessions/`.
- Every session tracks its UUID, auto-generated title (via Gemini Flash), session-specific genre constraint, chronological `chat_history`, and cumulative token costs.

#### **Frontend State (`frontend/renderer.js`)**
- Integrates an auto-save mechanic: after every AI interaction, the frontend state pushes the current chat array and metrics to the backend.
- Provides a "Gemini Web App" style floating drawer interface to allow real-time browsing, context-swapping, renaming, and deletion of past sessions without interrupting the Ableton flow.

---

## 3. The Execution Flow (The "Pre-Execution RAG" Pipeline)

When a user submits a complex sound design request (e.g., *"Load an Operator and give it a heavy sub bass"*), the system executes a multi-turn, state-aware pipeline:

**Phase 1: Session JIT Augmentation**
Before the prompt hits the LLM, the Backend queries the MCP Proxy for `ableton://session/state`. This massive payload (containing all current tracks, clips, and volumes) is appended to the user's prompt so the AI has perfect environmental awareness.

**Phase 2: Turn 1 (Context Gathering)**
The `CreativePlannerAgent` reasons that to build a sub bass, it needs an Operator and specific oscillator parameters. Because it operates under strict "Do Not Guess" system instructions, it outputs a JSON array containing *only*:
- `search_device_parameters(device_name="Operator", intent="Sub oscillator gain and filter cutoff")`
The Backend's ReAct loop intercepts this, prevents local execution, runs the `RetrieverAgent` against the JSON catalog, and feeds the precise parameter strings back into the Planner's context.

**Phase 3: Turn 2 (Compilation & Execution)**
Armed with the exact strings (`"Osc-D Level"`, `"Filter Freq"`), the Planner compiles the final JSON execution script:
1. `load_instrument_or_effect("Instruments/Operator")`
2. `set_device_parameter_batch([{"parameter_name": "Osc-D Level", "value": 1.0}, ...])`
3. `ui_text_response("### Manual Actions Required: Adjust the macro knobs...")`

The ReAct loop recognizes mutations, breaks the loop, and securely streams these commands sequentially through the MCP Proxy to mutate the active Ableton session.

---

## 4. Schemas and Tooling (`backend/schema.py`)
All tools are strictly typed using Pydantic, ensuring Gemini's "Structured Outputs" format perfectly matches the Python function signatures.
- **Key Schemas:** `InjectMidiRequest`, `LoadDeviceRequest`, `SetDeviceParameterBatchRequest`.
- **RAG Schemas:** `SearchDeviceParametersRequest`, `RetrieverSearchResponse`, `RetrievedParameterInfo`.

## 5. Summary
This asymmetric architecture shifts the heavy burden of API memorization away from the Pro model and onto a static JSON catalog powered by a fast, cheap Flash model. This completely eliminates hallucinations during device configuration and provides the user with an extremely reliable, unified generative music workflow.
