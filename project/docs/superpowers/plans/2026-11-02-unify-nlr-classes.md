# Canonical NLR class cleanup

User explicitly authorizes data migration: VAN -> MD, CAR -> LD; unify application and all project databases on LD/MD/HD. MEDIUM_TRUCK -> MD and HEAVY_TRUCK -> HD complete the old four-value vocabulary. This is project policy, not a claim that every real-world van is MD.

- [x] Add failing strict-class and migration tests (including backups, idempotency, schema/other-field preservation).
- [x] Remove runtime legacy aliases and ALL facility bypass; only LD/MD/HD are recognized. Missing evidence stays UNKNOWN.
- [x] Update seed/import generators, UI labels and regression fixtures to canonical values. Keep model names/source free text unchanged.
- [x] Add DAL ORM migration, backup and migrate the three existing project DBs. Compare schema and all non-class fields before/after.
- [x] Update current documentation and portable sample ZIP; preserve raw NLR/OCM/OSM source files and source-manifest rows.
- [x] Run full unit/integration/architecture/browser tests, review, and commit only requested files.

Existing synthetic demo becomes MD; clearance remains UNKNOWN, so its daytime overall NEEDS_REVIEW is intentional. Existing sample CAR profiles become LD and retain their existing behavior.

## Results
- RED: 9 strict-input/migration failures before implementation. Final full suite: 224 passed, 95 subtests; one existing Starlette/httpx deprecation warning.
- Backups: .work/class-backups/1-pluggedin.sqlite-backup, 2-pluggedin.sqlite-backup and 3-nlr_ocm_sample20.sqlite-backup. Audit: .work/class-migration-audit.json.
- Each old demo DB: 1 vehicle and 5 station class fields VAN -> MD. Active sample: 4 vehicles CAR -> LD. In total 6 vehicle rows and 10 station rows changed.
- Every schema and all other fields compared equal to the backups. All 6 non-DB source/metadata/manifest fingerprints unchanged. Migration reruns report zero changes.
- Independent read-only reviewer verified the same database/schema/column comparisons and found no important defects. Portable ZIP refreshed; no merge or push performed.
- Application follow-up: replaced free-text/datalist grade input with a native LD/MD/HD select (optional blank), and declared the same three enum values in the API schema. Legacy submissions return 400 with escaped original value preserved. Two tests failed before the change; final full suite: 226 tests and 95 subtests passed. Independent review found no important regressions. No DB changes in this follow-up.
