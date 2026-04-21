# **Architecture Evolution: Moving to a Hybrid Cloud/Local Pipeline**

**Date:** April 19, 2026

**Status:** Approved / Transitioning

## **Executive Summary**

The AbletonMCP orchestrator is transitioning from a purely localized LLM orchestration loop to a **Hybrid Cloud/Local "Context Diet" Architecture**. This change addresses severe cognitive overload and JSON syntax hallucinations encountered when passing 40+ Ableton tools to a quantized local model (Gemma 26b) during complex compound prompts.

By introducing a blazing-fast cloud model (gemini-3.1-flash-lite) as a semantic pre-router, we can dynamically filter the tool payload, allowing the local GPU model to execute tasks flawlessly without context dilution.

## **1\. The "As-Is" Architecture (Current State)**

The system bridges a Large Language Model orchestrator with Ableton Live via three major decoupled components:

1. **Frontend**: Electron/Web UI (NDJSON streaming).  
2. **Backend**: FastAPI Server \+ AI Orchestrator (gemini\_client.py).  
3. **Ableton Live Remote Script**: A TCP Server (127.0.0.1:9877) managing a thread-safe queue to execute commands deep inside Ableton's Python API.

### **Current Data Flow**

1. User sends a chat message.  
2. gemini\_client.py constructs a payload containing the chat history and the **entire suite of 40+ JSON-schema Ableton Tools**.  
3. The payload is sent to a localized Ollama instance (`qwen2.5-coder:14b`).  
4. Ollama selects a tool, Python executes it via the MCP Proxy, and the result is fed back into Ollama until the task is complete.

## **2\. The Problem: Why Change Direction?**

During extensive stress-testing of "Compound Prompts" (e.g., *"Put an appropriate device on track 2... Then add a clip"*), the purely local orchestration loop completely collapsed.

We identified three critical architectural ceilings for 16GB VRAM quantized models:

* **Cognitive Overload (Context Dilution):** Forcing the local model to read the schemas of 40+ irrelevant tools on every turn overwhelms its attention mechanism. It loses track of the user's actual prompt and panics, constantly defaulting to calling get\_session\_info.  
* **The "Naked Token" JSON Trap:** When overwhelmed by compound tasks, the model's JSON parser breaks. It fails to write standard {"name": "tool"} arrays and instead outputs raw internal formatting tokens (e.g., \<tool\_call|\>), resulting in infinite sub-second loops that flood the proxy.  
* **Hallucination by Penalty:** Attempting to fix the infinite loop by applying an engine repeat\_penalty severely backfires. Because valid JSON requires repeating syntax (like curly brackets and the word "name"), the penalty algorithm forbids the model from writing valid tool calls. The model is forced to hallucinate garbage text for 5 minutes until a system timeout occurs.

### **The Cost vs. Experience Dilemma**

Beyond purely technical limitations, this architectural pivot is driven by the need to find the perfect equilibrium between cost-efficiency and user experience.

* **The Pure Cloud Route:** Shifting the entire orchestration pipeline to a premium cloud model (e.g., Gemini 3.1 Pro) would easily solve the cognitive bottlenecks. However, this introduces unpredictable, recurring API costs for the user and requires transmitting sensitive session data externally for every minor action.  
* **The Pure Local Route:** Remaining 100% local guarantees zero-cost operation and absolute privacy. Yet, as our stress tests revealed, it severely degrades the user experience by causing unacceptable wait times (5+ minute hanging loops) and constant task failures on complex commands.

**Conclusion:** We must strike a balance. Generic local models are highly intelligent for single atomic tasks but structurally incapable of massive multi-tool JSON orchestration. By utilizing a highly optimized, low-cost cloud model strictly as a high-speed "routing brain" and reserving the free, local GPU for the heavy lifting of execution, we guarantee a seamless, instantaneous user experience without sacrificing the financial accessibility of a local AI tool.

## **3\. The "To-Be" Architecture (Future State)**

To solve this without reverting to an entirely expensive cloud-based execution model, we are implementing a **"Context Diet" Pre-Router**.

We separate the pipeline into two phases: **The Brain** (Cloud) and **The Hands** (Local).

### **New Component: The Semantic Tool Router**

We will inject a lightweight routing method (\_route\_tools) into gemini\_client.py, powered by Google's gemini-3.1-flash-lite.

### **New Hybrid Data Flow**

1. **The Intent Check (Cloud)**: When the user submits a prompt, Python sends *only* the user's text and a lightweight list of tool descriptions to gemini-3.1-flash-lite.  
2. **The Fast Filter**: Flash-Lite evaluates the intent and returns a strict JSON array of only the necessary tool names (e.g., \["load\_device\_to\_track\_by\_name", "create\_clip"\]) in \~400ms at near-zero cost.  
3. **The Context Diet**: Python filters the massive original tools array down to just these 2 tools (forcefully appending baseline context tools like get\_session\_info).  
4. **The Execution (Local)**: The heavily reduced payload is sent to the local Ollama instance (Qwen 2.5 Coder 14b). Because the cognitive load is reduced by 95%, the local GPU effortlessly formats the correct JSON execution arrays, completing compound tasks with zero syntax hallucinations.

This ensures your private studio data stays local, API costs remain negligible, and compound prompts execute reliably.