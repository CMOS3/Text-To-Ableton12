# Project Compliance Audit: Text-to-Ableton vs GEMINI.md

This document outlines the current state of the `Text_To_Ableton` codebase against the newly updated `@GEMINI.md` Developer Persona configuration. It details what complies, what falls short, and provides a phased roadmap to achieve full architectural compliance, along with risk mitigation strategies.

## Current State Analysis

### ✅ What Complies (The Good)
- **Dependency Management & Infrastructure:** The project is using `uv` for package management, maintaining both `pyproject.toml` and a `uv.lock` file. The `.env` file is utilized via `python-dotenv` to handle secrets (e.g., `GEMINI_API_KEY`), strictly avoiding hardcoded secrets.
- **Input Validation:** Pydantic models are actively used for data validation at the API boundary (e.g., `schema.ChatRequest`, `schema.SaveSessionRequest`), satisfying the "Zero Trust" data integrity rule.
- **Testing Foundation:** An automated test skeleton is present via `pytest`. Files like `test_gemini_client.py`, `test_schema.py`, and `test_supervisor.py` exist, adhering to the required testing phase workflow.
- **Serialization Safety:** No usage of `pickle` was detected. The application relies on JSON for external communication and serialization.

### ❌ What Doesn't Comply (The Gaps)
- **Modular Design:** The project violates the rule to "prioritize small, focused modules (<300 lines)". 
  - `backend/gemini_client.py` is ~46KB (>1000 lines).
  - `remote_script/__init__.py` is ~38KB (>1000 lines).
- **Strict Type Safety:** While type hints are used for parameters (e.g., `req: schema.ChatRequest`), return types (e.g., `-> dict`, `-> StreamingResponse`) are missing across almost all functions in `main.py` and the backend logic.
- **Documentation:** Critical API endpoints and core logic methods lack PEP-257 docstrings explaining their purpose, parameters, and return values.
- **Defensive Coding:** Extensive use of `except Exception as e:` blocks returning generic string messages (e.g., `return {"status": "error", "message": str(e)}`) instead of structured logging with relevant IDs/state and custom exceptions.
- **Formatting & Linting Configuration:** `pyproject.toml` currently lacks strict formatting tool dependencies and configurations (e.g., `ruff` or `black`).

---

## Phased Roadmap to Full Compliance

The following roadmap ensures the codebase is systematically brought up to the strict standards defined in `GEMINI.md` without breaking existing functionality.

### Phase 1: Tooling Baseline & Formatting
**Goal:** Enforce automated compliance checks before significant code changes.
- **Action 1:** Update `pyproject.toml` to include `ruff` and `mypy` as development dependencies.
- **Action 2:** Configure `ruff` rules for strict formatting, line length, and automated import sorting.
- **Action 3:** Run `ruff format` and `ruff check --fix` across the `backend` and `remote_script` directories.
- **Impact:** Instantly standardizes the codebase. Eliminates stylistic debates and catches hidden syntactical bugs or unused imports before runtime.
- **Risks (Low):** Applying strict `ruff` and `mypy` rules retroactively will likely surface dozens of existing warnings. The immediate risk is a temporary drop in velocity while we clear the technical debt required to make the CI/CD pipeline green.

### Phase 2: Architectural Modularization
**Goal:** Break down monolithic files to comply with the <300 lines modularity rule.
- **Action 1:** Refactor `backend/gemini_client.py` into a `gemini/` package (e.g., `client.py`, `retriever.py`, `executor.py`).
- **Action 2:** Refactor `remote_script/__init__.py` into a modular package (e.g., separating session state handlers, transport controls, and device manipulation).
- **Impact:** Massive improvement in maintainability. Splitting monolithic files isolates state, prevents massive merge conflicts, and allows us to unit-test components in isolation.
- **Risks (High):** 
  - **Circular Imports:** Monoliths often rely on implicit shared state. Splitting them can easily introduce circular dependencies.
  - **Ableton API Constraints:** The `remote_script` operates within Ableton's embedded Python interpreter, requiring a specific class structure and entry point (`create_instance`). Over-modularizing without understanding the Live Object Model's lifecycle could cause the script to silently fail on boot.

### Phase 3: Strict Type Safety & Documentation
**Goal:** Achieve 100% type coverage and adhere to PEP-257.
- **Action 1:** Audit all function signatures and append precise return types.
- **Action 2:** Add comprehensive docstrings to all non-trivial classes, methods, and FastAPI endpoints.
- **Action 3:** Run `mypy` strict mode to ensure no `Any` types are leaking through the boundaries.
- **Impact:** Transforms the codebase into a self-documenting system. Strict return types ensure IDEs and tools can trace data flow accurately, drastically reducing runtime `TypeError` and `AttributeError` crashes.
- **Risks (Low):** The primary risk is writing an incorrect type hint that satisfies `mypy` but masks a runtime reality, creating a false sense of security.

### Phase 4: Defensive Coding & Error Handling
**Goal:** Implement fail-closed logic and structured logging.
- **Action 1:** Create a `core.exceptions` module for custom domain errors (e.g., `AbletonConnectionError`, `InvalidPromptError`).
- **Action 2:** Replace generic `try/except Exception` blocks with specific exception catching.
- **Action 3:** Implement structured JSON logging that passes local variables, session IDs, and context rather than raw string stack traces.
- **Impact:** Shifts the system from "silent failures" to "fail-closed with telemetry." Custom exceptions allow the frontend and the AI to understand exactly what went wrong and attempt self-correction.
- **Risks (Medium):** Refactoring generic error handlers changes the control flow of edge cases. If we are too specific, we might inadvertently allow a previously-swallowed edge case to bubble up and crash the event loop or the FastAPI server.

---

## Global Mitigation Strategy

To mitigate the architectural and operational risks outlined above, we will adhere strictly to the following execution protocols:

1. **Sequential Execution:** We will not modify core logic until the formatting and typing baselines (Phase 1 & 3) are established and merged. Tooling must protect the refactor.
2. **Atomic Commits & Branching:** As per `GEMINI.md`, the `remote_script` modularization will be done one isolated domain at a time (e.g., extracting `TransportControl` into its own file, committing, and verifying before touching `DeviceControl`). 
3. **Pipeline Verification:** We will heavily leverage the `/deploy-ableton` workflow to immediately transfer and test the `remote_script` inside Ableton after every single structural change, ensuring we catch initialization crashes instantly.
4. **Automated Test Skeleton Execution:** Before restructuring `gemini_client.py` or FastAPI endpoints, we will ensure the existing `pytest` suite passes, and add missing unit tests for areas we plan to decouple.
