# Token-Optimized Agentic Architecture Implementation Plan

This document proposes a new hierarchical architecture for the Ableton MCP integration, aimed at optimizing the balance between LLM token consumption and tool use fidelity, transitioning away from the current monolithic "one-shot" architecture.

## User Review Required
> [!IMPORTANT]
> The transition to a Hierarchical Multi-Agent System (HMAS) and Just-In-Time (JIT) context retrieval will fundamentally alter how prompts are assembled and routed. Please review the proposed structural changes, the updated model choices, and the Implementation Roadmap to ensure these align with the immediate development goals.

## Proposed Structural Changes

### 1. Hierarchical Multi-Agent Orchestration
We will split the monolithic agent in `gemini_client.py` into two distinct roles:
- **Master Orchestrator (`gemini-3.1-pro-preview-customtools`)**: Responsible for strategic planning, parsing complex user requests, and orchestrating worker agents. The `customtools` variant is selected because it strictly prioritizes registered custom functions over bash execution, ensuring stable agentic orchestration. We will utilize the `MEDIUM` thinking level to balance cost and performance for routing and planning.
- **Worker Agents (`gemini-3.1-flash-lite-preview`)**: The best fit for high-volume, cost-sensitive, latency-critical tasks like extraction, formatting, and MCP interaction. We will configure API settings to ensure precision: enforcing `thinking_config` (e.g., `minimal` or `low` based on sub-task), and strictly enforcing Structured Outputs (JSON Schema/Pydantic). 

### 2. Pull-Based Resource Fetching (JIT Context)
Transition from pushing the entire Ableton LOM state to using MCP's dynamic resource templates.
#### [MODIFY] backend/mcp_proxy.py & remote_script/__init__.py
- Expose resource endpoints (e.g., `ableton://tracks/{track_id}/clips`).
- Add capabilities to respond to resource fetch requests, rather than emitting the full state continuously.

### 3. Context Caching
Neutralize token overhead for the foundational context (persona, guardrails, tool schemas, and static Ableton LOM).
- **Implicit Caching (Primary Approach):** We will rely purely on Gemini's Implicit Caching to automatically discount up to 90% of token costs on repeated contextual prefixes. This eliminates storage fees and avoids the "Storage Trap." If performance or latency issues arise later, we can re-evaluate Explicit Caching.

### 4. Deterministic Execution & Structured Outputs
Ensure the Flash-Lite models strictly adhere to schema requirements by refactoring tool schemas into flattened, sub-task-specific Pydantic models.
**Tool Strategy:**
- **Re-use existing Base Tools:** Refactor schemas for `test_ableton_connection`, `get_song_scale`, `get_session_info`, `set_tempo`, `get_track_info`, `create_midi_track`, `set_track_name`, `create_clip`, `set_clip_name`, `add_notes_to_clip`, `get_browser_tree`, `get_browser_items_at_path`, `load_instrument_or_effect`, `load_drum_kit`, `get_notes_from_clip`, `delete_notes_from_clip`, `get_track_devices`, `get_device_parameters`, and `set_device_parameter`.
- **Re-use existing Compound Tools:** Refactor schemas for `set_track_volume_by_name`, `get_session_mix_status`, `inject_midi_to_new_clip`, and `sound_design`.
- **New Tools to Add:** `fetch_resource` (for JIT pulling of state via MCP URIs).

### 5. Token-Optimized State Serialization
Replace verbose JSON with TOON (Token-Oriented Object Notation). While ABC notation is optimized for symbolic music, **TOON is the superior format for this generalized application**. TOON can efficiently handle Ableton core library device additions, complex synthesizer parameters, routing matrices, *and* numerical MIDI event arrays without the data loss (e.g., MPE or micro-timing) associated with transcoding to ABC.

---

## Implementation Roadmap

To prevent code dependencies and accommodate robust testing, the implementation will follow these logical steps:

### Step 1: Schema Refactoring & Validation
- **Action**: Update `backend/schema.py` to convert all existing tool definitions (Base and Compound) into flattened, Pydantic-based schemas optimized for Gemini Structured Outputs.
- **Test**: Unit tests to verify that Pydantic properly parses and validates sample JSON payloads for each tool.

### Step 2: Serialization & Pull-Based Fetching (Backend <-> Ableton)
- **Action**: Implement TOON serialization in the Python backend. Update `mcp_proxy.py` and `remote_script/__init__.py` to support `fetch_resource` using URI templates, returning TOON-compressed state and ETags.
- **Test**: Integration tests calling the new MCP endpoints directly (bypassing the LLM) to verify correct state retrieval and TOON formatting.

### Step 3: Worker Agent Implementation
- **Action**: Create the `WorkerAgent` class in `gemini_client.py` using `gemini-3.1-flash-lite-preview`. Implement the JSON Patch Refinement loop for error self-correction.
- **Test**: Unit/Mock tests feeding the Worker Agent static text prompts and verifying it correctly executes the Pydantic schemas without semantic errors.

### Step 4: Master Orchestrator Implementation
- **Action**: Create the `SupervisorAgent` in `gemini_client.py` using `gemini-3.1-pro-preview-customtools`. Implement the delegation logic where the Supervisor assigns MCP fetch and execution tasks to the Worker.
- **Test**: End-to-End (E2E) conversational tests (e.g., "Add an Operator to Track 1") verifying the Supervisor -> Worker -> MCP -> Ableton flow.

### Step 5: Race Condition Mitigation (ETags)
- **Action**: Enforce ETag version checking during tool execution in `mcp_proxy.py`.
- **Test**: Concurrency tests simulating manual user adjustments in Ableton between the fetch and execution phases to ensure stale actions are rejected safely.

---

## Adversarial Review

> [!WARNING]  
> Identifying potential edge cases and failure modes before implementation.

1. **Race Conditions in State Synchronization (JIT Retrieval)**
   - **Failure Mode**: The LLM queries the state of a track, takes time to reason, and then issues a relative parameter change. In the intervening seconds, the user manually alters a parameter. The LLM's action will execute based on stale context, causing jarring audio spikes.
   - **Mitigation**: Implement **ETag/version checking**. An ETag (Entity Tag) is a unique identifier assigned to a specific version of a resource. When the LLM fetches the track state, it receives an ETag (e.g., "v1"). When it executes the tool, it includes "v1". If the user changed the track in the meantime, the DAW state is now "v2", and the tool execution will be cleanly rejected, mitigating the race condition.

2. **High Costs During Development / Testing**
   - **Failure Mode**: Running complex agentic workflows repeatedly during testing can rapidly drain budget limits.
   - **Mitigation**: Configure Google AI Studio Project Spend Caps to pause usage if a strict dollar amount is hit, preventing runaway API billing.

3. **Flash-Lite Thinking Overhead (Token Cost and Latency)**
   - **Failure Mode**: Over-utilizing the `thinking_config` on the Flash-Lite worker increases latency *and* token cost. Gemini's "thought tokens" generated during reasoning are billed as output tokens. Using a `HIGH` thinking level generates thousands of extra tokens per request.
   - **Mitigation**: Dynamically adjust the thinking level (`minimal` vs `low`) based on whether the worker is simply formatting data or doing a minor extraction task to keep output token billing low.
