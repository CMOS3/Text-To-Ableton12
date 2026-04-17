---
trigger: glob
description: Enforcement of specific Gemini model endpoints for reliable tool calling and intent routing.
globs: ["backend/gemini_client.py"]
---

# Gemini API Routing Rule

- **Intent Routing:** The system uses an intent router to select the appropriate Gemini model based on user intent.
- **Endpoints:**
  - `models/gemini-3.1-flash-lite-preview`: Used for simple, direct, single-step commands (e.g., 'play', 'stop', 'create a track'). This model acts as the intent classifier and handles fast, deterministic actions.
  - `models/gemini-3.1-pro-preview-customtools`: Used for complex reasoning, multi-step actions, and ambiguous requests (e.g., 'make a techno beat'). It provides structured, reliable tool calling capabilities necessary for advanced Ableton logic.