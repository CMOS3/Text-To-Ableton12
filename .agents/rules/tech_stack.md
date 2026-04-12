---
trigger: glob
description: Definition of the core tech stack (Python/Electron) and GUI wrapping standards.
globs: ["**/*"]
---

# Technology Stack Rules

- **Backend:** Python must be used for all core logic, internal backend services, and API processing.
- **GUI / Frontend:** The graphical user interface must be implemented as a web-based desktop wrapper (e.g., Electron), utilizing web standards (HTML/JS/CSS) contained within a desktop application shell.