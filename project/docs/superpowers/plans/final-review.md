# Final independent review — 2026-10-26

## Verdict

**Approved for the specified local school-project MVP. No remaining Critical (P0/P1) or Important (P2) defect was identified in this review.**

This is a whole-project source review of the new implementation, not a Git diff review: the parent Git directory was unavailable/read-only. No application or test source was changed. This report is the only review deliverable written.

## Scope and evidence

Read the development specification, approved design, implementation contract, task 1–3 reports, prior core review, and progress ledger. Inspected the application services, pure evaluator and validation boundaries, repositories/UoW, metadata normalization, schema initialization/validation, demo seed, presentation DTOs/routes/error handlers, templates/map code, application composition, packaging/README, and test coverage.

The reviewer did not rerun the full test suite or browser suite. The root subsequently supplied a final consolidated result: **118 tests passed + 91 subtests in 23.79 seconds**, with one upstream httpx deprecation warning. This includes the two Chromium scenarios covering no-JS CRUD/search/detail/second browser and tile-blocked mobile rendering with five markers and zoom controls. The root also reported passing dependency consistency and compilation checks, successful actual init/seed/validate reruns, and completion of `docs/verification.md`. These are supplied execution results, not fresh executions by this reviewer.

## Prior findings checked

- SQLite integer bounds are now enforced before repository binding for IDs and integer vehicle range. The application regression covers an oversized lookup and failed update with the original vehicle/connectors retained.
- Supplemental metadata now has a single normalization boundary. Invalid top-level/station/field shapes become conservative values, while an invalid or missing explicit INCOMPLETE declaration does not waive aggregate integrity. Original files are not rewritten during reads. Deferred aggregate validation consumes the normalized shape.
- UTC parsing catches representability overflow, and station-local conversion handles extreme datetime boundaries without an uncaught overflow. Unit regression covers both ends of Python's datetime range.

## Substantive review conclusions

- The original 13-table/65-column structure, role identifiers, original vehicle `class` column, foreign keys/delete actions and constraints are retained. Initialization inspects existing schema rather than replacing data. The schema validator preserves case-sensitive CHECK literals.
- Vehicle and accepted-connector replacement are enclosed by one transaction, including rollback after a late connector constraint failure. Driver and vehicle cascades remain independent. Repositories flush but do not commit; the UoW closes sessions and translates storage failures into controlled application errors.
- Demo writes check existing rows and metadata for conflicts, preserving differing user data. The documented database-commit/metadata-file gap is real and explicitly acknowledged; rerunning seed can complete an interrupted file installation.
- The evaluator retains FAIL/UNKNOWN precedence, evaluates each port's complete check set before candidate selection, preserves common facility failures for incomplete port lists, and uses only direct connector evidence. Membership decisions use the chosen driver and station-local arrival date. Missing power remains independent of connector compatibility.
- SSR and API share application services and reload stored profiles. Normal invalid CRUD forms preserve text and selection values with 400 HTML; success uses 303. API errors use the specified envelope. No-JS flows receive complete server-rendered contents.
- Map JSON uses Jinja `tojson`; popups use text nodes, and their destination URLs are generated from validated numeric IDs and the preserved instant. Ordinary template output remains autoescaped. Static mounting is limited to presentation assets. No unsafe HTML handling or DB-file exposure was identified.
- No login, authorization isolation, CSRF workflow, adapter functionality, or additional ownership relation was demanded by this review; these remain outside the explicitly approved MVP scope.

## Acceptance coverage assessment

- **V01–V08:** packaging/runtime evidence, architecture tests, entity/ORM column correspondence, independent connection FK checks, schema constraints, deferred roles, and 24:00 value/ORM checks.
- **V09–V18:** real application/HTTP persistence, browser CRUD, restart through a new database/application instance, independent cascades, rollback, form preservation, complete SSR, no-JS and tile-failure scenarios.
- **V19–V26:** unit tests for opening/closing, split overnight periods, incomplete evidence, facility state, preserved instant, current tzdata behavior, direct connector/current rules and ambiguous combinations.
- **V27–V36:** source inspection for adapter exclusion; membership boundaries/driver/network handling, guest policy, 81 AND combinations, port OR/incomplete common failures, restrictions/truck rules, output bounds, and original coordinate uniqueness tests.
- **V37–V40:** escaping checks and safe map construction, API error/duplicate tests, seed repeat/conflict preservation tests, and real CRUD changes followed by reevaluation.

The suite exercises behavior and persisted state rather than only mirroring implementation. Some acceptance items combine source inspection, integration checks and supplied browser evidence; the report does not imply that each V item has a separate end-to-end test. The root records final consolidated verification separately in `docs/verification.md`.

## Non-blocking documentation note

An inaccurate Leaflet directory reference in README was reported to the root and corrected to `pl/static/vendor`. Runtime template URLs already used the correct paths. No open documentation finding remains from this note.

## Limits

No production deployment, high-concurrency load, concurrent manual metadata-file edits, or hostile externally modified SQLite content was tested. Those are not promised by this local MVP. The earlier Git limitation prevents a commit-based provenance assertion. Approval applies to the inspected source and declared scope; the root's final required suite is reported green.
