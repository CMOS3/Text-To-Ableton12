---
trigger: glob
description: Enforcement of specific Gemini model endpoints for reliable tool calling.
globs: ["backend/gemini_client.py"]
---

# Gemini API Routing Rule

- **Endpoint Enforcement:** All calls to the Gemini API must explicitly use the following endpoint:
  `models/gemini-3.1-pro-preview-customtools`
- **Rationale:** This specific endpoint ensures that AI interactions prioritize structured, reliable tool calls over unstructured raw code generation.