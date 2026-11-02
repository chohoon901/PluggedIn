# Independent core review — 2026-10-26

## Scope and verdict

Reviewed `cmn` and `dal` against the development plan, approved design, implementation contract, and task-2 report. Presentation/HTTP code is excluded because it was still being implemented. No application source was edited. Existing test suites were not rerun; the focused reproductions below used a newly initialized and seeded temporary database beneath `.work`, then disposed of it.

**Spec compliance: substantially compliant, with input/error-boundary gaps requiring correction. Quality verdict: changes requested for two Important (P2) findings. No Critical findings identified.**

The core implements the intended pure-domain/DAL separation, detached snapshots, independent driver/vehicle selection, direct-only connector evaluation, fail/unknown precedence, common checks on incomplete port candidates, local-date memberships, 24:00 period mapping, atomic vehicle/connector updates, original cascade relationships, and deferred organization/aggregate checks. The supplied SQL and ORM models preserve the thirteen-table structure, original column names, checks, relationships, and indexes; initialization validates rather than replaces an existing schema. Seed conflicts preserve existing differing rows and metadata.

## Findings

### P2 — Reject integers that cannot be represented by SQLite before repository calls

Location: `src/ca/uvic/ecs/csc501/cmn/application/services.py:53–55` and `:84–87`.

`_id` accepts every positive Python integer, and the integer branch of `_number` checks integrality but has no storage bound. SQLite parameter binding only accepts signed 64-bit integers. As a result, a caller can submit a syntactically valid positive ID or vehicle range and receive an unhandled `OverflowError` instead of the specified input/not-found response. UoW only translates SQLAlchemy integrity/database exceptions, so this error escapes the application boundary. This affects reads as well as writes; transaction rollback does not provide a usable error to the caller.

Reproduced with a fresh seeded database and an `ApplicationService` wired to `SqlAlchemyUnitOfWork`:

```python
service.get_driver(9223372036854775808)
service.save_vehicle({
    "vin": "NEW00000000000001",
    "range_km": 9223372036854775808,
    "accepted_connector_ids": [1],
})
```

Both calls produced `OverflowError: Python int too large to convert to SQLite INTEGER`, with no application status code. The application's ordinary JSON/HTML error contract cannot be fulfilled for these user-controlled values.

Fix at the input boundary without altering the supplied DB schema: validate integer representability before binding. Oversized input values should become an `InputError` with a field error; an out-of-range requested identifier may alternatively be treated consistently as a missing ID. Cover both a lookup and an atomic vehicle update, verifying that an invalid update leaves the original vehicle and accepted connectors intact.

### P2 — Validate supplemental metadata shapes before dereferencing or building snapshots

Location: `src/ca/uvic/ecs/csc501/dal/metadata.py:8–12`, `:22–28`; related aggregate consumer `dal/validation.py:26`.

The reader handles unreadable files and invalid JSON conservatively, but valid JSON of the wrong shape bypasses that fallback. A top-level JSON array/null raises `AttributeError` at `content.get`. Per-station values also lack complete type checks: a non-string timezone reaches `ZoneInfo`, an array completeness value is tested against a set, and a scalar `unconfirmedFields` is passed to `tuple`. These can raise uncaught errors during otherwise valid station searches. `aggregate_issues` independently dereferences a station metadata value with `.get` without the station reader's dictionary guard, so malformed supplemental metadata can also crash unrelated driver/vehicle/membership writes during commit.

Reproduction on the same isolated seeded database:

```python
database.settings.metadata_path.write_text("[]", encoding="utf-8")
service.detail(1, 1, 1, "2026-10-26T19:00:00Z")
```

Observed: `AttributeError: 'list' object has no attribute 'get'`, with no application status code. No DB contents were damaged, but the optional metadata boundary makes station evaluation unavailable instead of retaining UNKNOWN evidence or reporting a controlled validation problem.

Validate the document and each station entry at one DAL boundary, normalize unsupported/missing field values to conservative metadata defaults, and have deferred aggregate validation consume that validated shape. Preserve the requirement that a missing or invalid INCOMPLETE declaration does not exempt required aggregate children; report that as a controlled validation conflict. Do not rewrite the original metadata file. Add focused cases for a top-level array, a non-object station entry, an invalid timezone type, and malformed `unconfirmedFields`.

## Additional review notes

- An extreme supported datetime boundary also exposes an unhandled exception: `service.detail(1, 1, 1, "0001-01-01T00:00:00Z")` raises `OverflowError: date value out of range` while converting UTC into Vancouver time. This is a low-frequency boundary-hardening observation rather than an additional Important finding; a controlled date-range validation response would improve it.
- No concrete defect was found in the central AND/OR evaluation behavior or ordinary atomic CRUD flow during source inspection. The existing passing unit/DAL/application test results were taken as supplied evidence, not independently rerun or extended to claim a full-suite pass.
- This review does not assert UI/API route correctness, browser behavior, concurrency robustness of simultaneous metadata edits, or production-scale performance. Those were outside the requested core pass.
