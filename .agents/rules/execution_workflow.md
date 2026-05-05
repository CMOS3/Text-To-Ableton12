# Execution Workflow and Testing

When executing multi-phase implementation plans, you must strictly adhere to the following workflow:

## 1. Phased Execution & Pausing
- Execute the plan **one phase at a time**.
- **STOP** immediately after completing a phase. Do not automatically proceed to the next phase.

## 2. Quality Test Plans
- Upon pausing at the end of a phase, generate and present a **Quality Test Plan**.
- The test plan must include:
  - **Automated/Execution Tests:** Tests or verifications that you (the AI) can run directly (e.g., unit tests, log checks, linting).
  - **Manual Tests:** Specific steps for the user to perform (e.g., UI interactions, Ableton Live checks).
- If tests fail, enter a debug phase to resolve the issues.

## 3. Explicit Approval
- You must wait for the user's **formal "go"** (explicit approval) before beginning the execution of the next phase.

## 4. Deployment Notifications
- You are authorized to use the `deploy-ableton` workflow to deploy changes.
- **CRITICAL:** Whenever you execute a deployment, you must explicitly notify the user so they know to reload the MIDI remote scripts in Ableton Live.

## 5. Version Control (Git)
- You are responsible for version control.
- Ensure logical Git commits are made as work progresses (e.g., at the end of a phase or significant milestone).
- Always explain to the user **what** was committed and **why**.
