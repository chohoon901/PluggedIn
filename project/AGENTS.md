# PluggedIn

Read docs/PluggedIn_Development_Plan_AI_Agent.md and the approved design before changing behavior.

- Python 3.12+, project venv, src package ca.uvic.ecs.csc501.
- cmn is pure domain/application; dal owns all persistence and file I/O; pl owns HTTP/SSR/static assets. main composes them.
- Preserve the supplied 13-table, 65-column schema and original constraints.
- Store full driver/vehicle/membership data in SQLite. Never add adapter ownership/conversion or driver-vehicle ownership.
- SSR must work without JS; forms use 303 redirect on success and 400 HTML with preserved input on invalid submissions.
- Write Korean explanations above domain fields. Preserve UNKNOWN when evidence is incomplete.
- Website copy, validation errors and evaluation explanations are English. Preserve the language of user-entered data and Korean developer comments.
- Arrival forms use native date/time controls with an explicit Pacific time (BC) default or UTC. Resolve local input on the server; keep aware API/legacy URL compatibility and no-JS Search now.
- Run venv/Scripts/python.exe -m pytest tests/unit tests/integration tests/architecture, then tests/e2e for UI changes.
- Do not overwrite existing DB/user changes during init or demo seed.

