# Nullable station roles and matched sample implementation plan

**Goal:** Deliver a runnable application and a new 20-station SQLite dataset on Sunghun_IDNull, based on Sunghun commit 239eebb.

**Authority:** The user's four explicit requirements supersede the original NOT NULL owner/operator constraints and connector-name normalization policy. All other schema constraints, 13 tables / 65 columns, and UNKNOWN policies remain.

**Architecture:** Keep source connector strings in connector_type; compare names through a pure domain enum/alias registry, including across different accepted connector IDs. Use a DAL-only, reproducible NLR/OCM importer with a source-ID join, conservative evidence rules, and companion metadata/provenance files. Configure the existing app to use the new sample DB and derive initial bounds from its stations (demo fallback retained).

## Tasks
- [x] Test nullable Station domain/ORM/foreign-key validation and missing role rendering, then update schema and models.
- [x] Test cross-ID connector aliases and uncertain/unknown families, then implement the enum and repository snapshot support.
- [x] Test import selection, provenance, preserved names, estimated power, missing evidence and refusal to overwrite; implement a 20-record Vancouver-area sample builder.
- [x] Generate DB, metadata and manifest; configure active sample; verify CRUD, search bounds, map markers, filters, time/membership/vehicle changes and no-JS rendering.
- [x] Run unit/integration/architecture and browser suites, independent review, then deliver DB and companion files.

## Decisions / progress
- Work in the user-requested branch in the existing checkout. Preserve unrelated modified LaTeX and deleted create_db_local.py.
- No fabricated owner/operator organization rows. Missing roles stay NULL; genuine OCM operators may be imported as operators, never inferred owners.
- Unknown source boolean defaults remain unconfirmed. Do not copy estimated OCM PowerKW into a confirmed output. Preserve source snapshots in the manifest.
- Keep source station data distinct from clearly synthetic driver/vehicle/membership profiles. No OSM import.
- DB metadata remains a companion JSON under the existing architecture, with a configurable metadata path. No extra DB tables or overloaded columns.
- Initial baseline without --basetemp hit host temporary-directory permissions; rerun under .work. This is an environment issue, not an application regression.
- RED: nullable/alias tests failed before implementation (12 failures); importer tests failed before importer existed (2 failures). GREEN: full final pytest with Chromium: 185 passed + 91 subtests, one existing Starlette/httpx deprecation warning. Five browser tests include the real sample's 20 map markers and no-JS night-hours failure.
- Verification used elevated execution for local HTTP/thread/browser tests after restricted execution hung. No application dependency changes were required.
- Output: 20 stations, 26 port summaries, 98 operating periods, 9 source-name connector entries, 2 synthetic drivers, 4 synthetic vehicles, 6 synthetic memberships. All owners NULL; 5 operators NULL. validate_database returned no issues.
- Independent read-only code review found no actionable defects. Original DB, source files and unrelated user changes were retained. No merge or push is part of this task.
