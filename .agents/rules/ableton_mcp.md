---
trigger: glob
description: Rules for TCP communication with Ableton Live via the MCP bridge on port 9877.
globs: ["backend/**/*", "remote_script/**/*"]
---

# Ableton MCP Communication Rule

- **Communication Protocol:** The application relies on the local `ahujasid/ableton-mcp` server to interface with Ableton Live.
- **TCP Routing:** The application must communicate with this server exclusively via **TCP port 9877**.
- **Network Binding:** To prevent external network vulnerabilities or unwanted access, all background MCP servers must be strictly bound exclusively to the **`127.0.0.1`** (localhost) interface. Binding to `0.0.0.0` is strictly prohibited.
- **Remote Script Deployment:** Modifications or deployment of the Ableton Remote Script must explicitly note that it must reside in:
  `D:\Sync\00 PC Sharing\Ableton\User Library\Remote Scripts`
- **Boilerplate Requirement:** Every Remote Script must inherit from `_Framework.ControlSurface.ControlSurface` and MUST include the `create_instance(c_instance)` function as the entry point.