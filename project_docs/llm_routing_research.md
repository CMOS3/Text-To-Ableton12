# Research Report: Asymmetric Multi-Agent Routing Architecture

Based on your suggestion to swap the roles of the Flash-Lite and Pro models, I have conducted an analysis of current LLM architectural patterns, their feasibility within our Ableton Live integration, and the projected impact on cost and performance.

## 1. Nomenclature of the Proposed Architecture

The architecture you are proposing is widely recognized in the AI engineering community under several names, typically falling under the umbrella of **LLM Routing** and **Asymmetric Multi-Agent Systems**. 

Specifically, this pattern is referred to as:
*   **The "Brain-Hands" or "Planner-Retriever-Executor" Pattern:** A large model acts as the "Brain" (creative reasoning, parameter generation), while a small, fast model acts as the "Hands" or "Retriever" (fetching the JIT context, validating schemas, routing the prompt).
*   **Dynamic LLM Routing:** A pattern where a "Router" (usually a fast, cheap SLM like Flash-Lite) intercepts a prompt, parses its intent, gathers necessary external data (like the Operator parameter dump), and dispatches the enriched prompt to a heavy reasoning model (Pro).
*   **Tiered / Cascade Architecture:** Tasks begin at the lowest tier (Flash-Lite). If the task requires deep creative reasoning (e.g., sound design intent mapping), it is escalated to the highest tier (Pro).

## 2. Feasibility in the Ableton MCP Project

**Status:** Highly Feasible and Architecturally Sound.

Currently, we are using the Pro model to parse the initial prompt and output a JSON list of tools to execute JIT, and then using Flash-Lite to actually execute those tools (e.g., figuring out which parameters map to a "Plucky Bass"). 
As we just discovered, Flash-Lite struggles with the massive context of a 195-item parameter dump and hallucinates parameter names because its attention span and "creative adherence" are lower than the Pro model.

By swapping their roles:
1.  **Flash-Lite as the Router/Gatherer:** The user prompt is sent to Flash-Lite. Flash-Lite is instructed *only* to identify what JIT context is needed (e.g., "The user wants to tweak Operator on Track 1. I need to fetch Operator's parameters.") and fetch it.
2.  **Pro as the Creative Executer:** The fetched JSON parameter dump and the original user intent are then bundled and sent to Gemini 3.1 Pro. Because Pro has a massive context window and elite reasoning, it can perfectly read the 195-parameter JSON, select the exact string `"Osc-A Level"`, and intelligently decide that its value should be `0.75` for a plucky bass.

This aligns perfectly with their respective strengths: Flash-Lite is excellent at fast, deterministic JSON tool calling (fetching state), while Pro excels at complex synthesis and strict instruction following over large contexts.

## 3. Impact on Performance and Latency

> [!TIP]
> **Performance Shift:** Faster initial routing, slightly longer creative execution.

*   **Current State:** Pro model takes ~5-10 seconds to read the initial prompt and decide which tools to call. Flash-Lite then takes ~1-2 seconds to generate the parameter tweaks.
*   **Proposed State:** Flash-Lite (Router) will intercept the prompt and fetch the Ableton state in ~1-2 seconds. The Pro model will then take ~5-10 seconds to generate the creative parameter tweaks.
*   **Net Latency Impact:** The overall time-to-completion will remain roughly the same (around 7-12 seconds), but the system will feel more responsive because Flash-Lite will start querying Ableton (JIT fetching) almost instantly after the user presses enter. 
*   **Reliability:** Hallucinations (like guessing "Oscillator A Level" instead of "Osc-A Level") will plummet. Pro models are significantly better at "Needle-in-a-Haystack" retrieval tasks, meaning it will correctly find the exact parameter names in the dump.

## 4. Impact on Token Costs

> [!WARNING]
> **Cost Shift:** Token costs will increase slightly compared to the current implementation, but overall cost efficiency will remain high.

*   **Current Cost Flow:** Pro model processes a small prompt (low input tokens). Flash-Lite processes a massive parameter dump (high input tokens, but cheap model).
*   **Proposed Cost Flow:** Flash-Lite processes a small prompt (virtually zero cost). Pro model must now ingest the large parameter dump context (e.g., the 20,000-character Operator JSON).
*   **Cost Breakdown:**
    *   Flash-Lite Input: $0.25 / 1M tokens.
    *   Pro Input: $2.00 / 1M tokens (8x more expensive).
*   **Analysis:** Passing the 195-parameter Operator dump to the Pro model will cost approximately 8x more per request than passing it to Flash-Lite. However, because a parameter dump is only roughly 4,000 tokens, the absolute cost to pass it to the Pro model is still incredibly small (roughly $0.008 per request). Given the dramatic increase in accuracy and the elimination of failed requests, the cost-to-reliability ratio is highly favorable.

## Summary Conclusion

Migrating to an **Asymmetric Multi-Agent Router Architecture** is the optimal solution for this project. It offloads the "dumb" fetching and routing to the cheap, fast model, and reserves the expensive, creative reasoning for the Pro model, which is exactly how modern enterprise LLM systems are designed. It completely bypasses the need to build complex Python fuzzy-matchers, relying instead on the inherent intelligence of the Pro model.
