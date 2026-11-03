# NLR vehicle classes and cmn package organization

User request: use NLR maximum vehicle class LD/MD/HD to evaluate vehicle access, keep data unchanged, place enums together and move domain entities out of cmn root.

## Decisions
- cmn/domain contains all 13 schema-preserving entities, entity validation, and domain/value_objects. Adapter was removed in 3f331c9; the original reorganization incorrectly preserved that omission. It is restored following user feedback and the development plan's explicit requirement. cmn/enums contains ConnectorFamily, VehicleClass and evaluation enums. Contracts/application/services remain separate in cmn.
- NLR rank is LD < MD < HD; unknown or absent values remain UNKNOWN. CAR is interpreted as passenger class LD without rewriting stored values. VAN remains UNKNOWN because body style does not establish weight class; this behavior was explained to the user after their clarification question. MEDIUM_TRUCK/HEAVY_TRUCK are legacy MD/HD aliases. Keep truck clearance UNKNOWN for MD/HD regardless of parking.
- New vehicle forms offer NLR LD/MD/HD. Existing stored labels remain displayable and round-trip without automatic rewriting. ALL remains an explicit legacy facility allowance, not a vehicle class.
- No database, source dataset, station metadata or manifest edits. Fingerprint all data before/after.

## Execution
- [x] Write failing enum/access/package architecture tests.
- [x] Move entities/value objects and enums; update every source/test import.
- [x] Implement enum-based access, shared service validation and English form options.
- [x] Update regression expectations for intentional behavior changes; verify real sample access improvement without writes.
- [x] Run full unit/integration/architecture/e2e, independent review and data hash comparison.

## Verification notes
- RED: 23 new enum/access/package cases failed before implementation. Latest unit/integration/architecture: 204 passed plus 91 subtests; Chromium: 5 passed.
- Read-only check on actual sample: vehicle raw CAR unchanged, access PASS at stations 4/10/11, UNKNOWN at remaining 17. No data file writes; all 9 original DB/CSV/JSON fingerprints match before and after.
- No schema/config changes. The legacy synthetic demo's VAN records intentionally become UNKNOWN without changing its data; full known-pass unit fixtures now explicitly use LD.
- Final full pytest with Chromium: 209 passed, 91 subtests, one existing Starlette/httpx deprecation warning. Independent read-only review imported all 74 source modules and found no important defects. Data hashes matched again after the full suite.
- Adapter correction: removed the architecture exemption, restored Adapter with original fields/validation in domain, and added regression coverage. RED had 2 missing-domain failures; full GREEN: 210 tests and 95 subtests passed, one existing warning. All 9 data fingerprints remain unchanged.
