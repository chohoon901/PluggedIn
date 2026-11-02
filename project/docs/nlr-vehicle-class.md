# NLR vehicle-class access and package organization

This implements the user's request to interpret NLR vehicle classes with the user-authorized class-only data migration; schema is unchanged.

## Source and comparison

NLR/AFDC `maximum_vehicle_class` defines LD as passenger vehicles (Class 1-2), MD as medium-duty (Class 3-6), and HD as heavy-duty (Class 7-8). It describes maximum physical access, not station capacity or every other access condition.

Source: https://afdc.energy.gov/data_download/alt_fuel_stations_format

`cmn/enums/vehicle_class.py` defines LD, MD, HD and UNKNOWN, ranked LD < MD < HD. Public access plus a known vehicle class within the facility maximum passes access for LD vehicles. MD/HD retain the existing truck-clearance review: a maximum or truck-parking flag alone does not prove bay clearance. A vehicle above the maximum fails. Missing/unrecognized values remain UNKNOWN. Only LD/MD/HD are recognized; ALL and old body-style labels are not runtime class values.

The user explicitly requested CAR -> LD, VAN -> MD, MEDIUM_TRUCK -> MD and HEAVY_TRUCK -> HD for existing project class fields. This is a conservative project migration policy, not a universal legal classification of every real van. These old tokens are rejected by new vehicle input validation. Only LD/MD/HD are accepted; case/spacing normalize to the canonical code. Model names and source free text are unchanged.

Both JSON and SSR vehicle CRUD accept NLR codes. The vehicle form uses a native select with LD/MD/HD plus an optional blank unknown choice. The API schema explicitly enumerates only LD/MD/HD; old body-style values are rejected before the use case. Invalid submitted values are escaped and displayed on 400 forms for input preservation. Evaluation evidence includes the raw and interpreted values. Existing installations with old class tokens must run the explicit backed-up class migration below; updated sample files and generators already use canonical codes. Restart the server to load changed application code.

## Layout

- `cmn/domain/`: all 13 schema-preserving domain entities, plus entity validation.
- `cmn/domain/value_objects/`: Location and DailyTime.
- `cmn/enums/`: ConnectorFamily, VehicleClass, CheckStatus, OverallStatus and ReasonCode.
- `cmn/contracts/`: snapshots, repository contracts, errors and evaluation result dataclasses. Evaluation enums are re-exported from their former contract module for compatibility, but defined only in enums.
- `cmn/application/` and `cmn/services/`: use cases and pure evaluation logic.

Commit 3f331c9 removed the Adapter domain class. The initial package reorganization incorrectly preserved that omission and exempted it from architecture validation. Adapter is now restored under cmn/domain, as required by the development plan. All 13 domain entities are checked against the unchanged 13-table/65-column schema; adapter remains an inactive reference, with no ownership or conversion feature.

## Existing data

The sample now stores LD for its four synthetic vehicles and retains 7 LD / 13 missing facility maxima. Under the new interpretation, 3 public LD facilities pass access for LD profiles. Other facilities need review for missing maxima or restricted eligibility. Connector, payment and opening checks still independently affect the final status.

The old synthetic demo and its generator now use MD for vehicle and facility limits. A/B/E remain NEEDS_REVIEW because MD/HD charging-bay clearance is not verified; definite failures still take precedence. Missing facility maxima are not filled in. All original schema definitions, other column values and source data were retained during migration.

## Updating another existing DB

Stop the app first. From the project directory run, substituting the actual database path:

```powershell
.\venv\Scripts\python.exe -m ca.uvic.ecs.csc501.dal.scripts.migrate_vehicle_classes --database "src/ca/uvic/ecs/csc501/dal/data/pluggedin.db" --backup ".work/class-backups/previous.sqlite-backup"
```

This ORM migration changes only vehicle.class and station.max_vehicle_class, makes a consistent SQLite backup before changes, refuses to overwrite backups, and is idempotent. It also works on the older NOT NULL owner/operator schema without modifying that schema. NULL and unrecognized source values are retained as unknown evidence. Model names such as Van are not class values and are preserved. Do not use seed_demo to migrate an existing database.
