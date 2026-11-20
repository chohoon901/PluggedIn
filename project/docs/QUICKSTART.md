# PluggedIn Quickstart (Windows)

This guide accompanies the executable [quickstart.ps1](../quickstart.ps1). A Markdown file explains the process; the PowerShell script actually prepares and starts the application.

## Before starting

Install Python 3.12 or later, Git and OpenLink Virtuoso. For the one-time import, obtain the team release containing the configured SQLite DB and companion metadata JSON. The running application uses the Virtuoso graph for station searches, CQ2 and CQ4, and all driver, vehicle and membership records.

### Configure the application graph

Start Virtuoso. The default authenticated endpoint is `http://127.0.0.1:8890/sparql-auth`. Check `app_sparql_endpoint`, `app_graph_iri`, `sparql_endpoint` and `rdf_dataset` in [config.properties](../src/ca/uvic/ecs/csc501/dal/config.properties) for a different installation. The public and authenticated endpoints must be on the same server for the import.

For an app-only Virtuoso instance, you can set `PLUGGEDIN_VIRTUOSO_ORIGIN` to its HTTP or HTTPS origin, including the port. The import and the running app will use that server for both SPARQL endpoints.

Each teammate can run Virtuoso locally and import the same team sample using this guide. To share live edits to the same data, run the application and its private graph on a team-managed host with access restricted to the team.

Create a dedicated Virtuoso user named `pluggedin_app` in Conductor. In **Interactive SQL**, have a Virtuoso administrator apply these permissions, adjusting the graph IRI to match the configuration. [OpenLink graph permissions](https://docs.openlinksw.com/virtuoso/rdfgraphsecurityintconfsec/)

The `nobody` default below applies to the entire `PrivateGraphs` group. On a shared installation, review the existing members and preserve their required access before changing this default. Check any existing accounts with blanket private-graph access as well. The app graph should be accessible only to the app account and its administrators before importing profiles.

```sql
GRANT SPARQL_UPDATE TO "pluggedin_app";
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 0, 1);
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('pluggedin_app', 0, 0);
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('pluggedin_app', 0, 1);
DB.DBA.RDF_GRAPH_GROUP_INS (
  'http://www.openlinksw.com/schemas/virtrdf#PrivateGraphs',
  'https://github.com/chohoon901/PluggedIn/graph/app/'
);
DB.DBA.RDF_GRAPH_USER_PERMS_SET ('https://github.com/chohoon901/PluggedIn/graph/app/', 'pluggedin_app', 3);
```

Supply `PLUGGEDIN_VIRTUOSO_USER` and `PLUGGEDIN_VIRTUOSO_PASSWORD` to the app process, or save the credential from the repository root using your Windows account. Windows encrypts the password for your account on this computer.

```powershell
New-Item -ItemType Directory -Force .\project\output | Out-Null
Get-Credential -UserName 'pluggedin_app' -Message 'PluggedIn Virtuoso account' |
    Export-Clixml -LiteralPath .\project\output\virtuoso-credentials.xml
```

## First run

From the repository root (`PluggedIn`), open PowerShell and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\project\quickstart.ps1 -Migrate
```

The execution-policy option applies to this PowerShell invocation. The script creates `venv/` if needed, checks Python and installs the project. `-Migrate` reads the SQLite snapshot and station metadata, checks that the target graph is private, and verifies all 13 mapped tables before marking the graph ready. It also applies the sample20 power and adapter evidence. Run `-Migrate` again with the same source to resume an interrupted import. A completed application graph is protected from re-import.

Open **http://127.0.0.1:8000/**. Keep the terminal open and use **Ctrl+C** to stop. The original SQLite file is retained as the migration source.

If the terminal is already inside `project/`, use `-File .\quickstart.ps1` instead.

## Later runs

Reuse the installed environment:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\project\quickstart.ps1 -SkipInstall
```

Omit `-SkipInstall` when dependencies need to be installed or refreshed. To use another port, append `-Port 8001` and open **http://127.0.0.1:8001/**.

## Check without starting a server

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\project\quickstart.ps1 -CheckOnly
```

This checks the existing Python environment and Virtuoso application graph. Missing credentials, missing data and failed validation return a nonzero exit code.

## Repeatable demonstration

### Charging queries (Virtuoso)

In **Fast Charging** (CQ2), enter a minimum power in kW and search. With the
current sample20 ratings, 50 kW includes Norgate Park and Kaslo, 250 kW returns
Kaslo, and 251 kW returns no matches. Norgate Park's 50 kW DC equipment is
documented by [Prism Engineering](https://www.prismengineering.com/projects/district-of-north-vancouver-ev-design-and-implementation/).
In **Adapter Finder** (CQ4), select any of the
four sample vehicles to see matching ports, addresses and adapter product links.
Use the vehicle and network eligibility information before charging.
**Adapter Finder** reads accepted connectors from the same graph as **Vehicles**.
To reapply the published power and adapter evidence to an existing sample20 app
graph, supply the same credentials and run
`python -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --sample-equipment`
using the project venv.

### Station search (Virtuoso)

With an unchanged sample, select **Sample member (synthetic)** (driver `1`) and the **J1772 test car (synthetic)** (vehicle `2`). Search for **2026-11-02 at 12:00 Pacific time (British Columbia)**, keeping the initial area and all statuses. The recorded result is **20 stations: 1 Available, 19 Needs review, 0 Unavailable**. The Available station is **SWTCH Energy, 5965 Student Union Blvd** (station `11`).

The report's simpler exact-ID SQL demonstration also uses vehicle `2`, but it returns **station `1`, with one matching port record**. It compares stored connector IDs only; the full application additionally interprets connector aliases and evaluates hours, access, and payment. These are different queries with different purposes.

## Rebuilding or repairing a missing sample

See the [repository README](../../README.md#rebuild-the-sample-from-source-files) and [sample provenance guide](sample20.md). Rebuild into a new directory using `import_sample` and the original CSV/OCM files. Do not run the old synthetic `seed_demo` against the populated sample. Preserve DBs containing user-entered records.

With an initialized Virtuoso graph and the two credential environment variables set,
you can also run `python -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000`
from the project venv.
