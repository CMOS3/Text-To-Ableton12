---
trigger: glob
description: Deployment mandate for Ableton Live Remote Scripts.
globs: ["remote_script/**/*"]
---

# Deployment Mandate

- **Automated Deployment:** Whenever you modify any file inside the `remote_script/` directory, you must automatically execute `.\remote_script\deploy.ps1` in the terminal to deploy the changes to the Ableton User Library.
- **Workflow Reference:** This mandate corresponds to the manual `/deploy-ableton` workflow.
