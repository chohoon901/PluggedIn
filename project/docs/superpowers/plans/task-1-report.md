# Task 1 — pure domain and evaluation report

Completed the shared contract from `implementation-contract.md` in `cmn`, excluding the root agent's `application/` area. No DAL, presentation, setup, or Git changes were made by this task.

## Files

- Original entities: `organization.py`, `site_owner.py`, `operator.py`, `network.py`, `station.py`, `connector_type.py`, `port.py`, `operating_period.py`, `adapter.py`, `vehicle.py`, `vehicle_accepts.py`, `driver.py`, `membership.py` under `src/ca/uvic/ecs/csc501/cmn/`.
- Shared pure normalization: `cmn/validation.py`.
- Value objects: `cmn/value_objects/daily_time.py`, `location.py`, and package initializer.
- Contracts: `cmn/contracts/errors.py`, `models.py`, `evaluation.py`, `repositories.py`, and package initializer.
- Pure evaluation: `cmn/services/evaluation.py`, package initializer.
- Tests: `tests/unit/test_domain.py`, `tests/unit/test_evaluation.py`.

The 13 entity dataclasses have exactly 65 original column fields. Every entity and snapshot/value/result field has a Korean explanation. Optional strings normalize to None, IDs/positive numbers/lengths are validated, coordinates and powers normalize using Decimal, and required relationship IDs cannot be None. Adapter retains its direction constraint but evaluation does not import or query it.

Vehicle retains precisely its eight original fields. Its accepted connector relationship and `accepts()` behavior are on `VehicleSnapshot`, as required by the shared interface. OperatingPeriod contains a local datetime using an inclusive opening and exclusive closing. Membership includes both date boundaries.

The evaluator reads no files, DB, environment, or system clock. It accepts one aware instant and uses zoneinfo for station local time. It implements all four checks with reason codes and evidence, conservative hours/status/access/connector/payment policies, 81 possible AND combinations, per-port OR evaluation, incomplete-port candidates, deterministic representative selection, Decimal power bounds, and quantity/power uncertainty warnings. A common facility failure retains a verified direct connector on the representative port when one exists.

## TDD and verification

1. Initial six domain tests failed explicitly because their modules were absent; after implementation, all six passed.
2. Twenty evaluation tests failed explicitly because the service was absent; after implementation, the complete initial unit suite passed.
3. Required foreign-ID validation and exact maximum Decimal output tests were added and observed failing, then corrected. Repository protocol import shadowing was reproduced before adding deferred annotations.
4. Common failure plus a faster incompatible port and unconfirmed quantity warning regressions were observed failing, then corrected.

Final command:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit -q
```

Final result: **34 passed, 89 subtests passed in 0.30s**.

Coverage includes 24:00 parsing and invalid clocks, opening/closing boundaries, Sunday/Monday split overnight periods, incomplete hours, invalid timezone, aware-time enforcement, Vancouver -07 on 2026-11-01 and 2026-12-01 using installed tzdata, facility status plus closed hours, restricted access and unknown classes, truck clearance, all three verified connector/current combinations, NACS/unverified current, incomplete ports preserving common failure, direct candidate selection, missing power, membership local dates and selected driver, network mismatch, guest payment, and unconfirmed guest/quantity metadata.

An independent dataclass field audit printed `Original entity classes: 13 Original column fields: 65`.

## Integration verification limits

A bare full pytest run stalled after two tests and was interrupted. A targeted application run using the default temp directory reported five setup errors before database fixture execution: pytest could not create numbered temporary directories under the Windows sandbox package's AC/Temp path. A full workspace-basetemp rerun also stalled after two tests and was interrupted when the root agent took ownership of the HTTP/TestClient diagnosis. No full-suite or browser success is claimed here. Root is running integration/browser verification independently.

No known remaining pure-domain behavior failures. Integration, presentation, DB, and browser completion remain the owning agents' responsibility.

## Core review follow-up — datetime conversion boundaries

Read the additional note in `core-review.md` and reproduced `OverflowError` before changing production code. The new pure evaluator regression evaluates both Python datetime boundaries: year 1 UTC converted to Vancouver and the final instant of year 9999 UTC converted to Auckland. Both subcases failed at `astimezone` in the RED run.

`_local_arrival` now handles conversion overflow conservatively, alongside unknown/invalid zones. It returns no local time, so opening and membership-date-dependent payment remain UNKNOWN; the original supported aware arrival instant is preserved. No historical-date ban or arbitrary year limit was added. The user-facing reason now states that the local time cannot be confirmed.

GREEN verification: `.\venv\Scripts\python.exe -m pytest tests/unit -q` → **35 passed, 91 subtests passed in 0.32s**. No integration or browser claim is added; the root agent owns those runs.
