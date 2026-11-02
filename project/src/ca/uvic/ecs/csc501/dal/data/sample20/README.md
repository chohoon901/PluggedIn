# NLR–OCM sample20

Branch: `Sunghun_IDNull`, based on Sunghun commit `239eebb`.

## Run the application

From the project directory:

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.validate_db
.\venv\Scripts\python.exe -m uvicorn ca.uvic.ecs.csc501.main:app --host 127.0.0.1 --port 8000
```

The branch config selects `dal/data/sample20/data/nlr_ocm_sample20.db` and its `station_metadata.json`. Do not run seed_demo against the real sample: the synthetic seed IDs intentionally overlap and its conflict checks will refuse. The original `dal/data/pluggedin.db` is preserved and uses the former NOT NULL schema; changing config alone does not migrate that old schema. Demo tests build separate databases from the current schema.

## Contents and evidence

20 source facilities around Vancouver; 2 clearly synthetic drivers, 4 synthetic CAR vehicle profiles and synthetic memberships. Driver 1 has memberships valid from 2026-01-01 through 2026-12-31; driver 2 has none. Vehicles 1/2/3/4 accept raw NLR names J1772COMBO/J1772/CHADEMO/TESLA respectively. No driver–vehicle ownership is implied.

Only DataProviderID=2 OCM records are joined, by their DataProvidersReference to NLR.ID. `source_manifest.json` contains each entire original row, mappings, decisions and source-file hashes. Source inputs are the user-supplied NLR CSV and ocm_bc.json; no OSM rows are imported. Importer selection is fixed and reproducible. OCM operator is not treated as the site owner. All 20 owners are NULL.

The database alone contains all 13 tables / 65 columns and all domain profiles. To retain timezone, provenance and UNKNOWN behavior in the app, keep the companion metadata JSON. `config.properties` in the portable sample root demonstrates the relative paths. This keeps the original metadata architecture without introducing a new table.

Source connector text is preserved, not rewritten. `cmn/connector_family.py` provides the equivalent of a shared Java enum/alias registry. Separate IDs such as NLR J1772COMBO and OCM CCS (Type 1) can match; CCS Type 2 does not match CCS Type 1. NACS/TESLA and unknown combinations do not become verified direct connections.

OCM matched connection power values are explicitly estimates: all imported power_kw values are NULL. Raw estimated values remain in the manifest. Quantities are recorded summaries and unconfirmed. Missing guest payment and truck parking booleans use required storage defaults plus unconfirmedFields. Raw NLR LD/MD/HD values are not silently converted to the application's CAR/VAN/TRUCK classification. These decisions intentionally leave NEEDS_REVIEW results; do not fabricate green statuses to make a demo look complete.

## Check condition changes

- Home search automatically covers the dataset; vehicle 1 matches the CCS1 aliases in station 1. Switching to vehicle 2 or 3 changes connector checks. Vehicle 4 retains unverified Tesla/NACS results.
- Use 2026-11-02 at 12:00 Pacific. Station 5 (NLR 329666, GSPLP TGO 05) is within its recorded 08:00–17:00 schedule. Change to 23:00 Pacific: opening FAIL and overall UNAVAILABLE. A missing facility class can still keep daytime overall NEEDS_REVIEW.
- Switch driver 1 to driver 2 at station 1: payment changes from membership PASS to UNKNOWN because guest payment is unconfirmed. Membership CRUD updates the same DB; no fictional real membership is asserted.
- The map uses exactly the SSR result coordinates/statuses. Explicit status filtering, mobile layout, no-JS search and tile-failure fallbacks remain available.
- Search now uses actual time; synthetic memberships expire after 2026-12-31.

## Rebuild into a fresh directory

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.import_sample --output-root src/ca/uvic/ecs/csc501/dal/data/sample20-rebuilt --csv "datasets/alt_fuel_stations (Sep 21 2026).csv" --ocm datasets/ocm_bc.json
```

An occupied output directory is rejected. The importer never overwrites an existing DB or modifies the source files. To use another output root, change both database_path and metadata_path in the app's DAL config, keeping paths inside DAL.
