---
trigger: glob
description: Enforcement of Single-Shot Compiler pattern via Gemini API.
globs: ["backend/gemini_client.py"]
---

# Model Routing Rule

- **Primary Orchestrator (Single-Shot Compiler):** The system uses **gemini-3.1-pro-preview** via the `google-genai` SDK as the primary agentic loop.
- **Workflow:**
  - The model receives a pre-fetched `session_info` combined with the user prompt.
  - The model prompt is injected dynamically with minified JSON schemas representing all available proxy tools.
  - The model makes exactly **ONE** API request. `tools=declarations` is NOT used natively.
  - The model's response runs with `response_mime_type="application/json"` and forcibly returns a JSON array: `[{"tool": "name", "args": {...}}]`.
- **Text & Advice Generation:**
  - Standard text outputs or answers are rendered through the synthetic tool `ui_text_response` within the JSON array workflow, bypassing the need for separate advice tools.