---
trigger: glob
description: Enforcement of specific Gemini model endpoints for reliable tool calling and intent routing.
globs: ["backend/gemini_client.py"]
---

# Gemini API Routing Rule

- **Hybrid AI Execution Chain:** The system orchestrates multiple models to balance speed, cost, and creativity:
  1. **Local Interception (Ollama - gemma4:e4b):** Zero-latency interception for atomic transport commands (play, stop, tempo).
  2. **Semantic Tool Filtering (Cloud Flash - gemini-3.1-flash-lite-preview):** Analyzes complex prompts to strictly filter the exposed tool schemas, preventing context bloat for the Pro model.
  3. **High-Level Reasoning (Cloud Pro - gemini-3.1-pro-preview-customtools):** Handles deep musical logic, multi-step orchestration, and creative sound design.
  4. **Sub-Agent Execution:** Specialized tasks (e.g., `design_sound`) use nested Pro model calls for autonomous native parameter manipulation.