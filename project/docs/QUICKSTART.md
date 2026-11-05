# PluggedIn Quickstart (Windows)

This guide accompanies the executable [quickstart.ps1](../quickstart.ps1). A Markdown file explains the process; the PowerShell script actually prepares and starts the application.

## Before starting

Install Python 3.12 or later and Git, then obtain the team release containing the 20-station NLR-OCM sample. The checkout must contain the configured SQLite DB and its companion metadata JSON. VS Code is optional.

## First run

From the repository root (`PluggedIn`), open PowerShell and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\project\quickstart.ps1
```

The execution-policy option applies to this PowerShell invocation; it does not change the machine's permanent policy. The script locates `project/` itself, creates `venv/` if necessary, checks Python, installs `requirements.txt` and the project, validates the selected database, and starts uvicorn.

Open **http://127.0.0.1:8000/**. Keep the terminal open; use **Ctrl+C** to stop. The script follows `project/src/ca/uvic/ecs/csc501/dal/config.properties`. It never runs `init_db` or `seed_demo`, rewrites DB configuration, or rebuilds a database. If validation fails, it stops and reports the error.

If the terminal is already inside `project/`, use `-File .\quickstart.ps1` instead.

## Later runs

Reuse the installed environment:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\project\quickstart.ps1 -SkipInstall
```

Use the first-run command again when dependencies need to be installed or refreshed. To use another port, append `-Port 8001` and open **http://127.0.0.1:8001/**.

## Check without starting a server

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\project\quickstart.ps1 -CheckOnly
```

This checks the existing Python environment and selected DB without installing packages, creating a virtual environment, or starting a server. Missing files and failed validation return a nonzero exit code.

## Repeatable demonstration

With an unchanged sample, select **Sample member (synthetic)** (driver `1`) and the **J1772 test car (synthetic)** (vehicle `2`). Search for **2026-11-02 at 12:00 Pacific time (British Columbia)**, keeping the initial area and all statuses. The recorded result is **20 stations: 1 Available, 19 Needs review, 0 Unavailable**. The Available station is **SWTCH Energy, 5965 Student Union Blvd** (station `11`).

The report's simpler exact-ID SQL demonstration also uses vehicle `2`, but it returns **station `1`, with one matching port record**. It compares stored connector IDs only; the full application additionally interprets connector aliases and evaluates hours, access, and payment. These are different queries with different purposes.

## Rebuilding or repairing a missing sample

See the [repository README](../../README.md#rebuild-the-sample-from-source-files) and [sample provenance guide](sample20.md). Rebuild into a new directory using `import_sample` and the original CSV/OCM files. Do not run the old synthetic `seed_demo` against the populated sample. Preserve DBs containing user-entered records.

For a manually controlled installation, use the commands in the [README](../../README.md#installation-and-quickstart).
