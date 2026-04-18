# **Text-to-Ableton: Architecture & Expansion Roadmap**

This document outlines the architectural evolution of the Text-to-Ableton application. It defines the current baseline ("As-Is"), the target state incorporating Hybrid AI pipelines ("To-Be"), and the step-by-step roadmap to achieve massive Live Object Model (LOM) expansion with near-zero API token overhead.

## **1\. As-Is Architecture (Current State)**

The current application relies on a robust 3-tier architecture that bridges a modern desktop UI, a Python AI orchestrator, and Ableton's internal Python API.

### **Core Components**

* **Frontend (Electron/Node.js):** Features the "Anthracite UI", real-time NDJSON streaming of agentic thoughts, and a Macro Manager.  
* **Backend (Python FastAPI):** Runs on 127.0.0.1:8000. Acts as the brain, hosting the gemini\_client.py and mcp\_proxy.py. It uses an **Intelligent Intent Router** to switch between Gemini 3.1 Flash-Lite (simple tasks) and Gemini 3.1 Pro (complex reasoning).  
* **Ableton Remote Script:** A custom TCP listener running inside Ableton on 127.0.0.1:9877. It receives JSON-RPC payloads and queues them onto Ableton's main thread via the update\_display callback to ensure thread safety.

### **Current Limitations**

1. **Tool Payload Bloat:** For complex tasks, the backend currently sends *all* available Compound Tool schemas to Gemini Pro. This is cheap at 15 tools, but will become financially unviable at 50+ tools.  
2. **Hardcoded Routing:** The current intent router relies on basic heuristics or paid Flash-Lite tokens to classify simple vs. complex prompts.  
3. **LOM Feature Ceiling:** The app currently supports a highly curated, but limited, subset of Ableton's capabilities (missing deep parameter automation, timeline manipulation, etc.).

## **2\. To-Be Architecture (Hybrid AI Pipeline)**

The target architecture introduces local, open-weight models (via Ollama) to serve as a zero-cost intelligent routing layer, combined with the "Cherry-Pick" Strategy to safely expand DAW capabilities.

### **The Hybrid Routing Engine**

Instead of hitting external APIs for every action, local LLMs intercept the traffic:

1. **The Zero-Cost Router (gemma4:e4b):** This lightweight, lightning-fast local model intercepts the user prompt. For simple requests ("Hit play", "Arm the bass track"), it generates the JSON-RPC execution payload instantly for free, bypassing Google's APIs entirely.  
2. **The Local Tool Selector (gemma4:26b):** When the e4b router flags a prompt as "Complex", the backend pings the heavier local 26b model. It acts as a Semantic Filter. It reads the user's prompt against your entire library of tools and outputs *only the names of the 3-5 tools needed*.  
3. **The Heavy Lifter (Gemini 3.1 Pro):** The backend takes the prompt and *only those 3-5 selected tool schemas*, sending them to Gemini Pro. Gemini handles the deep musical reasoning (e.g., chord progression generation) but at a fraction of the token cost.

### **The "Cherry-Pick" Strategy (LOM Expansion)**

To expand capabilities without breaking the Pydantic guardrails or UI streaming:

* **Look, Don't Touch:** We treat open-source forks like jpoindexter/ableton-mcp (which have 200+ reverse-engineered LOM commands) as textbooks.  
* **Compound Consolidation:** We port specific snippet logic into our remote\_script/\_\_init\_\_.py, but we *hide* them behind single, high-level Python macros in the backend. Gemini only sees the macro (e.g., apply\_rhythmic\_automation), keeping schema definitions tiny.

## **3\. The Implementation Roadmap**

To move safely from the As-Is state to the To-Be state, development should follow these phases:

### **Phase 1: Local Model Interception (The Router)**

* **Goal:** Eliminate API costs for basic transport and track commands.  
* **Action:** Install Ollama and pull gemma4:e4b.  
* **Integration:** Rewrite the backend Intent Router to ping http://localhost:11434. Instruct it to output the JSON payload for simple LOM commands directly, or return STATUS: COMPLEX to pass it up the chain.

### **Phase 2: Local Tool Selection (The Pre-Filter)**

* **Goal:** Prepare the architecture for a massive influx of new tools.  
* **Action:** Pull gemma4:26b locally.  
* **Integration:** When a prompt is flagged as complex, send the prompt and a lightweight list of all tool descriptions to 26b. Have it return a strict JSON array of required tool names. Dynamically build the Gemini Pro schema payload based on this array.

### **Phase 3: "Cherry-Picking" LOM Expansion**

* **Goal:** Map advanced Ableton features (Automation, Warp Markers, Scene triggers).  
* **Action:** Using the jpoindexter repository as a guide, begin porting atomic LOM commands into the TextToAbleton remote script.  
* **Integration:** Group these new LOM commands into high-level Compound Tools (like humanize\_and\_evolve\_clip) within gemini\_client.py and register them in the local tool selector.

### **Phase 4: Semantic Tool Retriever (RAG) - *Future Scale***

* **Goal:** Prevent local LLM context window exhaustion when tool count exceeds 100+.  
* **Action:** Replace the gemma4:26b full-list prompt with a lightweight Vector Database (e.g., ChromaDB or local FAISS).  
* **Integration:** Embed all Compound Tool descriptions. When a complex prompt arrives, perform a vector similarity search to instantly retrieve the top 5 tools, bypassing the need for a local LLM to read the entire tool menu.

---

## **4. Current Status (April 2026 Progress Report)**

As of mid-April 2026, the application is in an **Advanced Hybrid State**, with all foundational routing layers active.

### **Progress Highlights**

*   **Phase 1 (Local Interception):** [✅ COMPLETED] Atomic transport commands (`set_tempo`, `start_playback`, `stop_playback`) are successfully intercepted by `gemma4:e4b` for zero-cost execution.
*   **Phase 2 (Tool Filtering):** [✅ COMPLETED] Semantic tool filtering via Gemini Flash is operational, reducing schema bloat for Gemini Pro.
*   **Phase 3 (LOM Expansion):** [✅ COMPLETED] Deep LOM access (Browser Navigation, MIDI Note Manipulation, Device Parameter control) is already fully operational.
*   **Scale-Aware MIDI:** [✅ COMPLETED] The `add_notes_to_clip` tool now supports semantic pitch names (e.g., "C3") and is scale-aware.

### **Resolved Technical Inconsistencies**

1.  **Reporting Corrected:** The backend now accurately reports `gemma4:e4b (Local Router)` in the chain, resolving the reporting glitch.
2.  **Optimized Routing:** The intent routing has been unified, and the redundant Flash router now serves as a fall-back if the local model is offline.
3.  **Active Filtering Layer:** The semantic filtering layer is now fully integrated into the `chat` loop.