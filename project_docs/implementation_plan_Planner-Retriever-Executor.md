# Architecture Migration: Asymmetric Creative Assistant (Planner-Retriever-Executor)

## Goal Description
Shift the project's backend architecture from a traditional Supervisor-Worker model to an **Asymmetric Creative Assistant** (Planner-Retriever-Executor) model. 
Currently, the large model (Gemini 3.1 Pro) acts as a Supervisor delegating creative tasks to a smaller model (Gemini 3.1 Flash-Lite), which acts as a Worker. The Worker model is failing due to limited context retention and hallucination when dealing with large Ableton parameter dumps. 

We will invert this: The large model (`CreativePlannerAgent`) will handle all creative reasoning, precise parameter mapping, and MIDI composition. The small model (`RetrieverAgent`) will handle pure contextual retrieval, routing, and simple formatting tasks.

## Open Questions Addressed
1. **TOON Compression:** We will make TOON (Token-Oriented Object Notation) compression the standard across the board for all responses fetched from Ableton, effectively shrinking token footprints globally.
2. **Agent Renaming:** We will rename `SupervisorAgent` to `CreativePlannerAgent` and `WorkerAgent` to `RetrieverAgent` to accurately reflect their new roles.
3. **Race Condition Mitigation (ETags):** While still part of the long-term roadmap, ETags are deprioritized. The `CreativePlannerAgent`'s tools will execute absolute changes (e.g., `set_parameter(value=0.5)`), mitigating the immediate risk of asynchronous state drift.

---

## Proposed Changes (Logical Roadmap)

### Phase 1: Global TOON Compression Optimization
To allow the `CreativePlannerAgent` to ingest full Ableton track states without token bloat, all data returned by the proxy must be optimally compressed.

#### `[MODIFY] remote_script/__init__.py`
- Locate the `_send_response` method.
- Modify it to automatically apply `self._to_toon()` to the `data` payload if it is a list or dictionary, before wrapping it in the standard `{"status": "success", "data": ...}` JSON structure.
- Remove redundant manual TOON compression from individual handlers (like `_do_fetch_resource`).

### Phase 2: Refactoring Schemas for Creative Control
We must give the `CreativePlannerAgent` access to direct "knobs and dials" tools rather than "intent-based" delegation tools.

#### `[MODIFY] backend/schema.py`
- Delete `SoundDesignRequest` and `WorkerInjectMidiRequest`.
- Rename `WorkerNoteSchema` to `SemanticNoteSchema`.
- Update `InjectMidiRequest` to accept a list of `SemanticNoteSchema` (exposing `pitch_name` directly to the `CreativePlannerAgent`).
- Create a new `SetDeviceParameterBatchRequest` schema:
  - Fields: `track_index: int`, `device_index: int`, `parameters: List[TweakSchema]`.
  - `TweakSchema` fields: `parameter_name: str`, `value: float`.

### Phase 3: Agent Class Renaming & Logic Migration
Update the python backend to reflect the new architecture.

#### `[MODIFY] backend/gemini_client.py`
- Rename class `SupervisorAgent` -> `CreativePlannerAgent`.
- Rename class `WorkerAgent` -> `RetrieverAgent`.
- Remove the `sound_design` method entirely.
- Add a new method `set_device_parameter_batch(self, track_index: int, device_index: int, parameters: list)` that iterates over the parameters and sends individual `set_device_parameter` requests to the proxy.
- Modify `inject_midi_to_new_clip`:
  - Remove all delegation to the `RetrieverAgent` (no more `worker.execute_task`).
  - Update the method signature to accept the `notes` array directly from the LLM.
  - Apply the `_pitch_name_to_midi` conversion locally and execute the proxy request.

#### `[MODIFY] backend/main.py` & `backend/test_supervisor.py`
- Update all instantiation references from `SupervisorAgent` to `CreativePlannerAgent`.

### Phase 4: Prompt Engineering the Creative Planner
The `CreativePlannerAgent` must understand its new ReAct loop standard operating procedure.

#### `[MODIFY] backend/gemini_client.py`
- Overhaul the `system_instruction` block for the `CreativePlannerAgent`.
- Define the new workflow explicitly:
  1. **Analyze Intent:** Understand the user's musical goal.
  2. **Retrieve Context JIT:** If modifying a device, use `get_track_devices` and `get_device_parameters` to fetch the LIVE parameters of the track.
  3. **Execute:** Use `set_device_parameter_batch` to tweak parameters. **CRITICAL:** Instruct the LLM that it must ONLY use exact `parameter_name` strings parsed from the TOON dump. No guessing or synonyms.
  4. **Compose:** Use `inject_midi_to_new_clip` to write the semantic musical notes.

### Phase 5: Verification & Testing
- Start the frontend Electron application.
- Submit the vague prompt: *"I want a new bass track, with a deep roaring sound and a bassline that works well with the drums."*
- Verify JIT logs to confirm `get_device_parameters` fires.
- Verify TOON payload size in backend logs.
- Verify parameter hallucination is resolved and Ableton applies the tweaks.

---

## Verification Plan

### Automated Tests
- Run `test_supervisor.py` to ensure the `CreativePlannerAgent` can parse its tools without initialization errors.

### Manual Verification
- Deploy the updated remote script to Ableton Live using the `/deploy-ableton` workflow.
- Execute the end-to-end prompt via the frontend GUI.
- Check Ableton Live to ensure the clip is created, notes are semantically correct, and the specific device parameters have updated.

---
## User Review Required
The plan has been rewritten to be completely context-free for a new developer agent. Do you approve this roadmap to begin execution?
