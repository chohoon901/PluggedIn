# MVP access without charging-bay clearance gating

User explicitly defers physical charging-bay clearance evaluation. Current MVP access is the AND of recorded eligibility and NLR vehicle grade, LD < MD < HD. This supersedes the earlier mandatory MD/HD clearance UNKNOWN rule. Missing/unsupported grades remain UNKNOWN; over-limit and explicit public-access denial remain FAIL. Restricted/uncertain eligibility still needs review.

- Remove clearance gating from check_access and its unused enum property.
- Keep has_truck_parking data unchanged; it does not affect access. Keep the old reason-code enum reserved for compatibility, but do not emit it.
- Update tests across classes, parking flags, restrictions and over-limit cases. Restore the canonical MD synthetic demo's expected A/B/E AVAILABLE, C UNAVAILABLE, D NEEDS_REVIEW.
- Update current spec, README and form copy to explain the MVP scope. Preserve general physical-clearance disclaimers; a class PASS does not assert physical measurements were verified.
- No DB, schema, source or metadata changes.

RED: 10 class/clearance regression failures before implementation. GREEN: 235 unit/integration/architecture tests and 98 subtests passed. Independent read-only review found no important logic regressions. All DB/source/metadata fingerprints unchanged. Final browser-inclusive run recorded below.

Final full pytest with Chromium: 240 tests and 98 subtests passed; one existing Starlette/httpx deprecation warning. All 9 DB/source/metadata fingerprints matched again after testing.
