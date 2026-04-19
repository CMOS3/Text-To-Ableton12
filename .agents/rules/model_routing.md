---
trigger: glob
description: Enforcement of Local-First model orchestration via Ollama and Cloud Expert bypass.
globs: ["backend/gemini_client.py"]
---

# Model Routing Rule

- **Primary Orchestrator (Ollama):** The system uses **VladimirGav/gemma4-26b-16GB-VRAM** locally via Ollama (`127.0.0.1:11434`) as the primary agentic loop. It has a context window of 4096 and temperature 0.0.
- **Iterative Loop Management:**
  - The orchestrator iteratively calls tools based on Ollama's `tool_calls`.
  - A strict **MAX_ITERATIONS = 5** circuit breaker is enforced to prevent state bloat.
- **Cloud Expert Bypass:**
  - If the model determines it needs high-level production advice or complex guides, it must call `consult_cloud_expert`.
  - Calling this tool triggers a textual advice response from **Gemini 3.1 Pro** and **immediately halts** the local tool loop to preserve context and ensure the user reads the expert advice.