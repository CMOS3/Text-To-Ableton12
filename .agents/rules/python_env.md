---
trigger: glob
description: Standards for virtual environment usage and explicit interpreter paths.
globs: ["**/*.py", "requirements.txt", "pyproject.toml"]
---

# Python Environment Rule

- **Interpreter Directive:** All Python operations must use the explicit interpreter located at:
  `.\backend\.venv\Scripts\python.exe`
- **Virtual Environment:** A directory named `.venv` must be used. Create it using `python -m venv .venv` if it doesn't exist.
- **Dependency Management:** Never install packages to the global/system environment. Always maintain an up-to-date `requirements.txt` or `pyproject.toml`.
- **Execution:** All terminal commands (pip, python, pytest, etc.) must be run from within the activated environment or via the explicit path.