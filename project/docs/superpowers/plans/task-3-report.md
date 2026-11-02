# Task 3 — HTTP / SSR presentation report

## Delivered

- Implemented only the presentation package and `tests/integration/test_http.py`; this report records the handoff. No commits made.
- `pl.routes.router` includes the exact specified SSR and `/api/v1` CRUD, catalog, search, evaluate, and health routes. Database-using route handlers are synchronous. Services come exclusively from `request.app.state.services`; PL imports no DAL, session, ORM, or SQL implementation.
- Pydantic HTTP DTOs normalize optional blanks, reject extra/spoofed fields, validate VIN, lengths, positive numbers/IDs, selected connector set, membership dates, bbox order, status, and aware arrival timestamps. Input DTO fields have Korean meaning/unit comments.
- SSR forms render DB values and keep submitted values and connector selections after validation or service conflicts; failed form saves return 400, successful saves/deletes return 303. API create/get/replace/delete use 201/200/204, with uniform error envelopes and 400 instead of framework 422.
- Korean responsive interface: dark green navigation, warm paper background, lime/coral accents, CSS hero art, accessible labels/focus/skip link, status text and reason codes, CRUD lists/forms, filter counts, server-complete result cards, four-check detail/evidence, registered ports and schedules, organization roles, provenance, caveats, and Google Maps destination links.
- Server uses `tojson` for map data and HTML autoescaping throughout. No client API fetching, client profile storage, SPA, or adapter functionality. Search/detail preserve the service's single resolved arrival instant.
- Local pinned Leaflet 1.9.4 CSS/JS and original BSD license included under `pl/static/vendor`; OpenStreetMap attribution visible. Map popups use text nodes, not raw user HTML. Complete SSR results remain available without JS or tiles. Optional Google Fonts have system fallbacks.

## Verification evidence

- Tests were authored before route implementation. Initial execution first lacked installed pytest and then failed because the independently implemented DAL initialization module was not yet present. These setup failures were not counted as passing behavior checks.
- First complete HTTP run: **13 passed**, after dependencies and shared implementations were available.
- Added regression coverage for every SSR form/list, blank membership filter, conflict/date/selection restoration, real form edit/delete/cascade, and filtered/empty search results. This exposed `/memberships?driver_id=` returning 400; fixed blank-filter normalization and reran.
- Final dedicated command: `venv/Scripts/python.exe -m pytest tests/integration/test_http.py -q --basetemp=.work/pytest-pl-round3`: **27 passed**, one upstream Starlette/httpx deprecation warning, 8.57 seconds.
- Windows restricted execution blocked asyncio's local socketpair before TestClient startup. Repeating the test outside that restriction succeeded; this was an environment limitation, not an app hang.
- Root browser tests exposed a 390px mobile grid intrinsic-width overflow. Fixed actual grid column minimums and child minimum widths without hiding page overflow. Chromium inspection checked home, all three CRUD lists/new/edit forms, search, and detail: **12 pages, zero mobile overflow failures at 390×844**.
- Viewed `.work/mobile.png` and `.work/results.png`; desktop result capture shows the map controls and five status markers. Fixed retained fallback DOM before Leaflet creation and replaced a bad CDN stylesheet hash with verified local vendor files.
- Root reported both no-JS CRUD/search/detail/second-context and tile-failure browser scenarios passing after the responsive fix. Root owns the strengthened marker/control browser assertions and final full-suite run. An extra full-suite run started here was stopped upon root's request to avoid duplicate runs; no full-suite completion is claimed in this report.

## Contract / limitations

No ApplicationService contract changes required. PL independently generates a single aware UTC initial-form string; search/detail use the instant resolved by the shared service. External tiles and optional fonts still require network; library assets and all substantive results/forms are local. Map tile failure leaves markers and the full SSR list usable. A browser with JavaScript disabled uses the complete server-rendered list, detail, forms, and directions links.
