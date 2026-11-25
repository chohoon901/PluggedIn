# PluggedIn local setup for teammates

Use this guide to run PluggedIn on Windows or macOS with your own local Virtuoso. Use the team checkout that includes `715bb9f` (`Migrate PluggedIn storage to Virtuoso RDF`). The repository includes the `sample20` SQLite file and station metadata used to build the demo graph.

## 1. Prepare the project and Virtuoso

- You need Python 3.12 or later, Git, and a local OpenLink Virtuoso server. Use Conductor or the Virtuoso SQL client to manage the graph.
- If your checkout already tracks the team branch, run `git pull --ff-only` from the repository root. Run the terminal commands below after running `cd project` from the same directory.
- Start your Virtuoso server. The default HTTP address is `http://127.0.0.1:8890`. If you use Conductor, open `http://127.0.0.1:8890/conductor`. For a different port, use the value in the `[HTTPServer]` section of your Virtuoso configuration.

## 2. Prepare the private application graph

**If you have already used this guide's migration command**, reuse the application graph and account. Set up the connection in step 3, then follow **Update an existing application graph** in step 4.

**If you previously uploaded only RDF or are setting up the app for the first time**, prepare an application graph. The default graph for the earlier RDF upload is `https://github.com/chohoon901/PluggedIn/graph/`. Use the application graph name below for the migration.

```text
https://github.com/chohoon901/PluggedIn/graph/app/
```

If you manually loaded RDF under the application graph name, choose a new, empty graph name. Use it for `app_graph_iri` in the configuration file and in the SQL below so the migration can run alongside your earlier RDF. [config.properties](../src/ca/uvic/ecs/csc501/dal/config.properties)

On your local application instance, open **Conductor → Interactive SQL** or start a session in the Virtuoso SQL client as an administrator. Replace `YOUR_LOCAL_PASSWORD` with a password for the app account on this machine. If the `pluggedin_app` account already exists, skip the first statement.

The `nobody` setting below applies to the entire `PrivateGraphs` group on that instance. If other projects use the group or depend on existing account permissions, use a separate local Virtuoso instance before running the SQL. See the setup notes at the end of this guide. [OpenLink graph permissions](https://docs.openlinksw.com/virtuoso/rdfgraphsecurityintconfsec/)

```sql
DB.DBA.USER_CREATE ('pluggedin_app', 'YOUR_LOCAL_PASSWORD', VECTOR ('SQL_ENABLE', 1, 'DAV_ENABLE', 0));
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 0, 1);
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('pluggedin_app', 0, 0);
DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('pluggedin_app', 0, 1);
DB.DBA.RDF_GRAPH_GROUP_INS (
  'http://www.openlinksw.com/schemas/virtrdf#PrivateGraphs',
  'https://github.com/chohoon901/PluggedIn/graph/app/'
);
DB.DBA.RDF_GRAPH_USER_PERMS_SET ('https://github.com/chohoon901/PluggedIn/graph/app/', 'pluggedin_app', 3);
GRANT SPARQL_UPDATE TO "pluggedin_app";
```

## 3. Set up Python and the connection

Run the commands for your OS. If Virtuoso uses a different HTTP port, replace `8890` in `PLUGGEDIN_VIRTUOSO_ORIGIN`. For example, use `http://127.0.0.1:8893` for a local instance on port 8893. Run the remaining commands in the **same terminal** where you entered the password.

### Windows PowerShell

```powershell
if (-not (Test-Path .\venv\Scripts\python.exe)) { py -3 -m venv venv }
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -m pip install -e .

$env:PLUGGEDIN_VIRTUOSO_ORIGIN = 'http://127.0.0.1:8890'
$credential = Get-Credential -UserName 'pluggedin_app' -Message 'Local Virtuoso app account'
$env:PLUGGEDIN_VIRTUOSO_USER = $credential.UserName
$env:PLUGGEDIN_VIRTUOSO_PASSWORD = $credential.GetNetworkCredential().Password
Remove-Variable credential
```

If the `py` launcher is unavailable, check your Python version and use `python -m venv venv` to create the environment.

### macOS Terminal

```bash
if [ ! -x ./venv/bin/python ]; then python3 -m venv venv; fi
./venv/bin/python --version
./venv/bin/python -m pip install -e .

export PLUGGEDIN_VIRTUOSO_ORIGIN='http://127.0.0.1:8890'
export PLUGGEDIN_VIRTUOSO_USER='pluggedin_app'
printf 'Local Virtuoso app password: '
IFS= read -rs PLUGGEDIN_VIRTUOSO_PASSWORD
printf '\n'
export PLUGGEDIN_VIRTUOSO_PASSWORD
```

## 4. Load or update the sample data

### Load the ontology (TBox)

Before importing the instance data, load the RDF/XML ontology into a separate named graph in Virtuoso. This step is also applicable to an existing application graph.

1. Open Conductor and log in as an administrator.
2. Navigate to **Linked Data → Quad Store Upload**.
3. Select **File** and upload [PluggedIn.rdf](../src/ca/uvic/ecs/csc501/dal/semantic/PluggedIn.rdf).
4. Enter the following Named Graph IRI:

   ```text
   https://github.com/chohoon901/PluggedIn/graph/schema/
   ```

5. Click **Upload** and confirm that `Upload finished` appears.
6. Navigate to **Linked Data → Graphs** and verify that the schema graph exists.
7. Open **Linked Data → SPARQL** and execute the following query:

   ```sparql
   PREFIX owl: <http://www.w3.org/2002/07/owl#>

   SELECT ?type (COUNT(DISTINCT ?entity) AS ?count)
   WHERE {
       GRAPH <https://github.com/chohoon901/PluggedIn/graph/schema/> {
           ?entity a ?type .
           FILTER (?type IN (
               owl:Class,
               owl:ObjectProperty,
               owl:DatatypeProperty
           ))
       }
   }
   GROUP BY ?type
   ```

   Expected results:

   | Type | Count |
   | --- | ---: |
   | owl:Class | 12 |
   | owl:ObjectProperty | 11 |
   | owl:DatatypeProperty | 40 |

The ontology graph stores the schema (TBox), while the private application graph stores instance data (ABox). Keep these graphs separate. The application graph must be empty before its first migration, so do not upload the ontology into `graph/app/`.

This ontology-loading procedure and the expected declaration counts were verified on macOS using Virtuoso 07.20.3243.

### First run or previous RDF-only upload

Run the one-time import into the empty application graph. It reads the SQLite snapshot and station metadata included in Git. The initial sample prints `Verified 193 SQLite records in the private Virtuoso graph.` The import also adds the charging power and adapter evidence.

**Windows**

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso
```

**macOS**

```bash
./venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso
```

### Update an existing application graph

Stop the app, update the checkout, then run the command below. `Sample20 equipment evidence is ready.` confirms that the power and adapter evidence has been applied. You can rerun the command because identical triples are stored once. [SPARQL update applied by this step](../src/ca/uvic/ecs/csc501/dal/semantic/queries/sample20_equipment_evidence.ru)

**Windows**

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --sample-equipment
```

**macOS**

```bash
./venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --sample-equipment
```

## 5. Start the app

Check for `Virtuoso application graph is ready.` before starting the app server.

**Windows**

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --check
if ($LASTEXITCODE -eq 0) {
    .\venv\Scripts\python.exe -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
}
```

**macOS**

```bash
./venv/bin/python -m ca.uvic.ecs.csc501.dal.scripts.migrate_to_virtuoso --check &&
  ./venv/bin/python -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
```

Open the app in your browser. Stop it with **Ctrl+C** in its terminal. The next time you run it, start Virtuoso and return to step 5. In a new terminal, set the connection variables in step 3 again. [Open PluggedIn](http://127.0.0.1:8000/)

## 6. Demo steps and expected results

1. In **Find charging**, select `Sample member (synthetic)` and `J1772 test car (synthetic)`. Set the date to `2026-11-02`, the time to `12:00`, and the time zone to `Pacific time (British Columbia)`. Click **Find stations**. With the initial sample and default search area, expect **20 stations** with **1 Available, 19 Needs review, and 0 Unavailable**. Open **SWTCH Energy (5965 Student Union Blvd)** and check that **Direct connection** shows **Pass**.
2. In **Fast Charging (CQ2)**, `0` or `50` kW returns **Kaslo** and **Norgate Park**. `250` kW returns **Kaslo**, and `251` kW returns no results. Norgate Park is rated at 50 kW and has two rows, one for each connector type. [Norgate Park installation evidence](https://www.prismengineering.com/projects/district-of-north-vancouver-ev-design-and-implementation/)
3. In **Adapter Finder (CQ4)**, select a sample vehicle and click **Search stations**. Each sample vehicle has at least one candidate. Show the station, the direction from port connector to vehicle inlet, and the adapter product link. The results match connectors. Check vehicle and charging network eligibility before using a candidate.
4. Open **Drivers**, **Vehicles**, and **Memberships** to inspect the demo profiles. To demonstrate persistence, use **Drivers → Add driver** with a new synthetic licence number, verify the record in a fresh browser window, then edit and delete it.
5. Run **CQ1 and CQ3** to show their result tables. Copy both `PREFIX` declarations and one `SELECT` at a time. Use your application graph in `GRAPH`. In **Interactive SQL**, add `SPARQL` on the first line and `;` at the end. In the initial sample, **CQ1** returns one BC Hydro DoubleTree location and its coordinates. **CQ3** returns eight direct-connection matches in Vancouver. [sparql_queries.rq](../src/ca/uvic/ecs/csc501/dal/semantic/queries/sparql_queries.rq)

## Troubleshooting

- **Connection or authentication error**. Check that Virtuoso is running, that `PLUGGEDIN_VIRTUOSO_ORIGIN` uses the HTTP port, and that the app account can connect.
- **The graph already contains data**. Run `--check` first. If the graph is ready, use the existing-graph command in step 4. For a graph that was populated by manual uploads, choose an empty application graph name in step 2.
- **Private-graph error or `RDF99`**. Check the graph name and permissions from step 2. If the existing Virtuoso instance also serves other private graphs, switch to an app-only local instance.
- **Only Kaslo appears at 50 kW**. Verify that the checkout has the latest app code, run the existing-graph command in step 4, and restart the app.
- **Port 8000 is in use**. Change `--port 8000` to `--port 8001` in the startup command. [Open the app on port 8001](http://127.0.0.1:8001/)

### Run a separate local Virtuoso instance if needed

Copy the example `virtuoso.ini` from your installed Virtuoso into a new, empty working directory. Check that the database, transaction log, lock file, and temporary database paths point inside the new directory. Use two free ports, for example `127.0.0.1:1113` for `ServerPort` under `[Parameters]` and `127.0.0.1:8893` under `[HTTPServer]`. In the new directory, run your installed Virtuoso server executable with `-f -c virtuoso.ini`. Use port 8893 for Conductor, 1113 for the SQL client, and `http://127.0.0.1:8893` in step 3. [OpenLink server configuration](https://docs.openlinksw.com/virtuoso/ch-server/)

### Apply just the RDF additions manually

Apply the update file to a graph that already contains the same `sample20` stations and ports. Set every `GRAPH` to the target graph and remove comment lines starting with `#`. In **Interactive SQL**, add `SPARQL` at the beginning and `;` at the end before running it. Use the latest CQ2 query in the app to see the new results in the UI. [sample20_equipment_evidence.ru](../src/ca/uvic/ecs/csc501/dal/semantic/queries/sample20_equipment_evidence.ru) · [Virtuoso execution example](https://docs.openlinksw.com/virtuoso/rdfindertmethodsparqlendpoint/)
