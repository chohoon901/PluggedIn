# Task 2 — DAL implementation report

Implemented the shared public contract without interface changes:

- DAL-confined Settings and SQLite engine/session factory; no automatic schema creation. Every engine connection enables foreign keys and the configured busy timeout.
- Thirteen separate ORM model files, all 65 original columns, original `vehicle.class` mapping, unique/check constraints, foreign keys/delete actions, eight indexes, and role tables with `WITHOUT ROWID` metadata.
- `scripts/schema.sql` extracted verbatim from specification §13.
- Domain mappers, detached aggregate snapshots, CRUD repositories, and request-scoped UoW. Vehicle connector replacement is one transaction. Deferred validation rejects organizations without roles, owners/operators without stations, vehicles without accepted connectors, and stations without required children unless explicitly marked INCOMPLETE.
- Non-destructive initialization; exact schema inspection against an in-memory execution of the original DDL; integrity/FK/aggregate inspection; executable init/seed/validate modules.
- Specification §9 ORM demo seed in one DB transaction. Existing identical rows are retained, changed rows/metadata report conflicts, and malformed existing metadata is preserved. Station metadata file I/O remains entirely inside DAL.

## Verification

Latest scoped command:

```powershell
$env:PYTHONPATH='src'
.\venv\Scripts\python.exe -m pytest tests/integration/test_database.py -q --basetemp=.work/pytest-db
```

Result: **24 passed in 4.45s**.

Coverage includes original DDL constraints, schema/ORM column and named-constraint correspondence, real per-connection FK activation, FK deletion actions, detached reads/24:00 mapping, seed idempotence/conflict preservation, atomic failed vehicle replacement, CRUD cascades, deferred role/aggregate rules, missing metadata fallback, config path containment, non-destructive init, damaged schema/index detection, and case-sensitive CHECK literal inspection.

Test-first execution initially encountered missing pytest, then missing package installation while dependencies were being provisioned. After those environment dependencies were ready, the scoped tests ran successfully. Additional regression tests demonstrated failures for malformed metadata overwrite, missing named ORM checks, and case-insensitive schema literal comparison before the corresponding fixes.

A full `pytest -q --basetemp=.work/pytest-db-all` run was started; it printed two passes then waited on browser setup without further output. It was interrupted at the root agent's request; full-suite/browser verification remains with the root agent. No full-suite pass is claimed here.

## Operational detail

The SQLite demo relationship writes are committed together. The metadata JSON is atomically replaced afterward because SQLite cannot transactionally commit a separate JSON file. If that file write fails, the DB relationship rows remain intact and rerunning seed can complete metadata installation.

No commits were made and no files owned by the other implementation tasks were changed.

## Core review P2 follow-up — metadata shape boundary

Reproduced the review defect before implementation: top-level JSON `[]` and `null` produced two failing regression cases with `AttributeError`; the entry/field matrix then produced 16 additional expected failures (and two existing-safe cases). These exposed scalar/list entries crashing aggregate validation, invalid field types escaping snapshots, and malformed uncertainty lists confirming defaults.

The metadata reader now validates document, station-entry, timezone, completeness, source, and uncertainty-list shapes at one DAL boundary. Invalid values become conservative read defaults. A malformed uncertainty list retains valid strings and marks guest-payment, truck-parking, and quantity evidence unconfirmed. Snapshot display defaults remain distinct from an explicit valid `INCOMPLETE` declaration, so corrupt metadata cannot waive missing required station children. Deferred aggregate checks consume the same normalization, including metadata supplied by seed.

Reading and validation leave the original JSON untouched. Seed compares and preserves the original document instead of persisting normalized read defaults.

Latest scoped verification:

```powershell
.\venv\Scripts\python.exe -m pytest tests/integration/test_database.py -q --basetemp=.work/pytest-db-review-green
```

Result: **44 passed in 7.73s**. The twenty added cases cover top-level arrays/null, station scalars/lists/null, non-string and unknown timezones, malformed completeness/source values, scalar/mixed uncertainty lists, controlled aggregate conflicts and rollback, invalid INCOMPLETE declarations, evaluation without type crashes, and byte-preservation of metadata files.

The required unit/integration/architecture run was also started. It advanced without reported failures before stalling at restricted HTTP execution. At the root agent's request, that run was interrupted; the root owns the final full-suite run with approved local networking. No new full-suite pass is claimed by this task.
