"""실제 Chromium에서 무JS/타일 실패/저장 유지와 전체 demo 흐름을 검증한다."""
import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import expect


@pytest.fixture
def live_app(tmp_path):
    from ca.uvic.ecs.csc501.dal.database import Database
    from ca.uvic.ecs.csc501.dal.settings import Settings
    from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
    from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
    from ca.uvic.ecs.csc501.main import create_app
    database = Database(Settings(dal_root=tmp_path / "dal"))
    init_database(database)
    seed_demo(database)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(database), host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started, "Test server did not start"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)
    database.engine.dispose()


@pytest.mark.e2e
def test_no_javascript_crud_search_detail_and_second_browser(browser, live_app):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(live_app + "/drivers/new")
    page.locator('[name="licence_number"]').fill("E2E-LIC-001")
    page.locator('[name="name"]').fill("브라우저 운전자")
    page.locator('[name="carrier_name"]').fill("테스트 운송사")
    page.locator('form button[type="submit"]').click()
    expect(page.locator("body")).to_contain_text("브라우저 운전자")
    second = browser.new_context(java_script_enabled=False)
    other = second.new_page()
    other.goto(live_app + "/drivers")
    expect(other.locator("body")).to_contain_text("E2E-LIC-001")
    page.goto(live_app + "/stations?driver_id=1&vehicle_id=1&arrival_at=2026-10-26T19%3A00%3A00Z")
    expect(page.locator("body")).to_contain_text("Demo A")
    expect(page.locator("body")).to_contain_text("Demo D")
    detail_link = page.locator('a[href^="/stations/1?"]').first
    expect(detail_link).to_have_count(1)
    detail_link.click()
    expect(page.locator("body")).to_contain_text("Demo A")
    expect(page.locator('a[href*="google.com/maps"]')).to_have_count(1)
    expect(page.locator("body")).to_contain_text("100")
    page.goto(live_app + "/drivers/3/edit")
    page.locator('[name="name"]').fill("수정된 운전자")
    page.locator('form button[type="submit"]').click()
    expect(page.locator("body")).to_contain_text("수정된 운전자")
    page.goto(live_app + "/vehicles/new")
    for name, value in {"vin": "E2E00000000000001", "licence_plate": "E2E-02", "make": "Demo", "model": "Browser van", "vehicle_class": "VAN", "range_km": "250", "max_charge_kw": "100.5"}.items():
        page.locator(f'[name="{name}"]').fill(value)
    page.locator('[name="accepted_connector_ids"][value="1"]').check()
    page.locator('form button[type="submit"]').click()
    expect(page.locator("body")).to_contain_text("Browser van")
    page.goto(live_app + "/vehicles/2/edit")
    expect(page.locator('[name="max_charge_kw"]')).to_have_value("100.5")
    page.locator('[name="model"]').fill("Updated van")
    page.locator('form button[type="submit"]').click()
    expect(page.locator("body")).to_contain_text("Updated van")
    page.goto(live_app + "/memberships/new")
    page.locator('[name="driver_id"]').select_option("3")
    page.locator('[name="network_id"]').select_option("1")
    page.locator('[name="start_date"]').fill("2026-01-01")
    page.locator('[name="end_date"]').fill("2026-12-31")
    page.locator('form button[type="submit"]').click()
    expect(page.locator("body")).to_contain_text("수정된 운전자")
    page.goto(live_app + "/memberships/3/edit")
    page.locator('[name="end_date"]').fill("2027-01-01")
    page.locator('form button[type="submit"]').click()
    expect(page.locator("body")).to_contain_text("2027-01-01")
    page.locator('form[action="/memberships/3/delete"] button').click()
    expect(page.locator('a[href="/memberships/3/edit"]')).to_have_count(0)
    page.goto(live_app + "/vehicles")
    page.locator('form[action="/vehicles/2/delete"] button').click()
    expect(page.locator("body")).not_to_contain_text("Updated van")
    page.goto(live_app + "/drivers")
    page.locator('form[action="/drivers/3/delete"] button').click()
    expect(page.locator("body")).not_to_contain_text("수정된 운전자")
    second.close()
    context.close()


@pytest.mark.e2e
def test_map_tile_failure_preserves_server_results(browser, live_app):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.route("**/*tile.openstreetmap.org/**", lambda route: route.abort())
    page = context.new_page()
    page.goto(live_app + "/stations?driver_id=1&vehicle_id=1&arrival_at=2026-10-26T19%3A00%3A00Z")
    expect(page.locator("body")).to_contain_text("Demo A")
    expect(page.locator("body")).to_contain_text("Demo E")
    expect(page.locator('a[href^="/stations/1?"]').first).to_be_visible()
    expect(page.locator(".leaflet-control-zoom")).to_be_visible()
    expect(page.locator(".leaflet-overlay-pane path")).to_have_count(5)
    expect(page.locator(".map-fallback")).to_have_count(0)
    assert page.locator("html").evaluate("el => el.scrollWidth <= window.innerWidth + 1")
    context.close()


@pytest.mark.e2e
def test_calendar_time_search_and_search_now_work_without_javascript(browser, live_app):
    from datetime import datetime, timezone
    from urllib.parse import parse_qs, urlparse
    context = browser.new_context(java_script_enabled=False, locale="en-US")
    page = context.new_page()
    page.goto(live_app + "/")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.get_by_label("Driver", exact=False).select_option("1")
    page.get_by_label("Vehicle", exact=False).select_option("1")
    page.get_by_label("Date", exact=True).fill("2026-10-26")
    page.get_by_label("Time", exact=True).fill("12:00")
    expect(page.get_by_label("Time zone", exact=True)).to_have_value("America/Vancouver")
    page.get_by_role("button", name="Find stations").click()
    expect(page.locator("body")).to_contain_text("Demo A")
    expect(page.locator("body")).to_contain_text("Oct 26, 2026 at 12:00 PM")
    link = page.locator('a[href^="/stations/1?"]').first
    assert parse_qs(urlparse(link.get_attribute("href")).query)["arrival_at"] == ["2026-10-26T19:00:00+00:00"]
    link.click()
    expect(page.locator("body")).to_contain_text("Oct 26, 2026 at 12:00 PM")
    page.get_by_role("link", name="Back to results").click()
    page.get_by_label("Date", exact=True).fill("")
    before = datetime.now(timezone.utc)
    page.get_by_role("button", name="Search now", exact=True).click()
    expect(page.locator("body")).to_contain_text("Demo A")
    href = page.locator('a[href^="/stations/1?"]').first.get_attribute("href")
    instant = datetime.fromisoformat(parse_qs(urlparse(href).query)["arrival_at"][0])
    assert before <= instant <= datetime.now(timezone.utc)
    context.close()


@pytest.mark.e2e
def test_english_calendar_forms_fit_mobile_screen(browser, live_app, tmp_path):
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="en-US")
    page = context.new_page()
    for path in ("/", "/drivers/new", "/vehicles/new", "/memberships/new", "/stations?driver_id=1&vehicle_id=1&arrival_date=2026-10-26&arrival_time=12:00", "/stations/1?driver_id=1&vehicle_id=1&arrival_at=2026-10-26T19%3A00%3A00Z"):
        page.goto(live_app + path)
        expect(page.locator("html")).to_have_attribute("lang", "en")
        assert page.locator("html").evaluate("el => el.scrollWidth <= window.innerWidth + 1"), path
    page.goto(live_app + "/")
    page.screenshot(path=str(tmp_path / "english-arrival-mobile.png"), full_page=True)
    context.close()
