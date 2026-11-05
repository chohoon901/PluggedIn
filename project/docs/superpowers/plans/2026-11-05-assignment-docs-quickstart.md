# Assignment corrections and Quickstart Implementation Plan

> **For agentic workers:** Execute inline with the existing approved design and the user's four correction requests. No application behavior or schema changes.

**Goal:** Correct the report to match the implementation, preserve the SELECT structure with a working vehicle ID, repair root README links, and provide a real Quickstart script plus a short guide.

**Architecture:** Documentation and a PowerShell setup wrapper only. The wrapper delegates persistence validation to the existing DAL command and never initializes or seeds a database. Preserve source data and user profiles.

**Tech Stack:** LaTeX/acmart, Markdown, Windows PowerShell, existing Python 3.12+ virtual environment, SQLite read-only verification.

**Spec:** User's current correction request; `docs/PluggedIn_Development_Plan_AI_Agent.md`; approved 2026-10-26 design and 2026-11-02 nullable-reference/sample amendment.

## Global constraints

- Preserve the supplied 13-table, 65-column schema and all user data.
- Do not add adapter evaluation or ownership.
- Produce an updated report copy; preserve the original submission ZIP.
- Root README edits are explicitly requested; stage and verify them before writing outside the project workspace.

## Review focus

- Exact-ID SQL matching: vehicle 1 returns no rows, while vehicle 2 returns a recorded match; do not invent extra matching ports.
- Shared organization keys and table-specific key names must be described accurately.
- The current populated sample must not receive synthetic demo seed rows.
- The setup wrapper must stop on validation errors and must not rewrite DB configuration.
- Links must resolve from the repository-root README, including restored SQL examples and new Quickstart documentation.

## Tasks

- [x] Correct the report's model, constraints, membership, adapter, and setup descriptions; change both SELECT literals to vehicle 2 and show the verified output.
- [x] Fix the LaTeX ampersand, retain the requested figures, and compile a three-page reviewable PDF and source ZIP.
- [x] Add `quickstart.ps1` with install/start, check-only, and skip-install paths; add `docs/QUICKSTART.md` and restore the linked SQL example file.
- [x] Repair all root README relative links and stale setup-guide references without overwriting unrelated edits.
- [x] Verify query results, Quickstart check-only/start behavior, all local README links, PDF rendering, ZIP contents, and unchanged data fingerprints.
