---
trigger: glob
description: Enforcement of Single-Shot Compiler pattern via Gemini API.
globs: ["backend/gemini_client.py"]
---

# Model Routing Rule

- **Primary Orchestrator (Single-Shot Compiler):** The system uses **gemini-3.1-pro-preview-customtools** via the `google-genai` SDK as the primary agentic loop.
- **Workflow (Pre-Execution ReAct Loop):**
  - The model receives a pre-fetched `session_info` combined with the user prompt.
  - The model prompt is injected dynamically with minified JSON schemas representing all available proxy tools.
  - The model is allowed to make multiple API requests during a single interaction by outputting "Context-Gathering" tools (like `fetch_resource` or `search_device_parameters`). The backend will intercept these, run them, and feed the result back to the model.
  - The final model response must run with `response_mime_type="application/json"` and forcibly return a JSON array containing mutation tools: `[{"tool": "name", "args": {...}}]`.
  - **Action Preview (Dry-Run)**: The system can intercept the generated array, pause execution via `asyncio.Event`, and wait for user approval via the frontend.
- **Text & Advice Generation:**
  - Standard text outputs or answers are rendered through the synthetic tool `ui_text_response` within the JSON array workflow, bypassing the need for separate advice tools.