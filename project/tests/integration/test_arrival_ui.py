"""Consumer date/time entry remains explicit about station-local time without JS."""
from datetime import datetime, timezone
import json
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient


class FormDocument(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.inputs = {}
        self.links = []
        self.back_url = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name"):
            self.inputs[attrs["name"]] = attrs
        if tag == "a" and attrs.get("href", "").startswith("/stations/1?"):
            self.links.append(attrs["href"])
        if tag == "a" and attrs.get("class") == "back-link":
            self.back_url = attrs.get("href")


@pytest.fixture
def client(tmp_path):
    from ca.uvic.ecs.csc501.dal.settings import Settings
    from ca.uvic.ecs.csc501.dal.database import Database
    from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
    from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
    from ca.uvic.ecs.csc501.main import create_app
    db = Database(Settings(dal_root=tmp_path))
    init_database(db)
    seed_demo(db)
    with TestClient(create_app(db)) as http:
        yield http
    db.engine.dispose()


def instant_from_results(response):
    assert response.status_code == 200, response.text[:500]
    document = FormDocument(response.text)
    return parse_qs(urlparse(document.links[0]).query)["arrival_at"][0]


def test_home_has_native_date_and_time_pickers_in_pacific_time(client, monkeypatch):
    from ca.uvic.ecs.csc501.pl.routes import pages
    monkeypatch.setattr(pages, "now_string", lambda: "2026-10-26T19:00:46+00:00")
    response = client.get("/")
    document = FormDocument(response.text)
    assert document.inputs.get("arrival_date", {}).get("type") == "date"
    assert document.inputs.get("arrival_time", {}).get("type") == "time"
    assert document.inputs["arrival_date"]["value"] == "2026-10-26"
    assert document.inputs["arrival_time"]["value"] == "12:00"
    assert 'name="arrival_at"' not in response.text
    assert "Pacific time" in response.text


@pytest.mark.parametrize("zone, expected", [("America/Vancouver", "2026-10-26T19:00:00+00:00"), ("UTC", "2026-10-26T12:00:00+00:00")])
def test_calendar_time_converts_explicit_zone_and_detail_keeps_instant(client, zone, expected):
    response = client.get("/stations", params={"driver_id": 1, "vehicle_id": 1, "arrival_date": "2026-10-26", "arrival_time": "12:00", "arrival_timezone": zone})
    assert instant_from_results(response) == expected
    document = FormDocument(response.text)
    assert document.inputs["arrival_date"]["value"] == "2026-10-26"
    assert document.inputs["arrival_time"]["value"] == "12:00"
    detail = client.get(document.links[0])
    assert detail.status_code == 200
    assert expected in detail.text
    assert "Oct 26, 2026" in detail.text


def test_existing_aware_urls_restore_friendly_fields(client):
    response = client.get("/stations", params={"driver_id": 1, "vehicle_id": 1, "arrival_at": "2026-10-26T19:00:46+00:00"})
    assert instant_from_results(response) == "2026-10-26T19:00:46+00:00"
    document = FormDocument(response.text)
    assert document.inputs["arrival_time"]["value"] == "12:00"
    assert "Oct 26, 2026" in response.text


@pytest.mark.parametrize("date_value,time_value,zone", [
    ("2026-10-26", "", "America/Vancouver"),
    ("", "12:00", "America/Vancouver"),
    ("2026-02-30", "12:00", "America/Vancouver"),
    ("2026-10-26", "25:00", "America/Vancouver"),
    ("2026-10-26", "12:00", "Unrecognized/Zone"),
    ("2025-03-09", "02:30", "America/Vancouver"),
    ("2025-11-02", "01:30", "America/Vancouver"),
])
def test_invalid_or_ambiguous_local_time_is_400_with_preserved_fields(client, date_value, time_value, zone):
    response = client.get("/stations", params={"driver_id": 1, "vehicle_id": 1, "arrival_date": date_value, "arrival_time": time_value, "arrival_timezone": zone})
    assert response.status_code == 400
    document = FormDocument(response.text)
    assert document.inputs["arrival_date"]["value"] == date_value
    assert document.inputs["arrival_time"]["value"] == time_value
    assert 'value="1" selected' in response.text


def test_search_now_ignores_stale_time_without_javascript(client):
    before = datetime.now(timezone.utc)
    response = client.get("/stations", params={"driver_id": 1, "vehicle_id": 1, "arrival_date": "2020-01-01", "arrival_time": "12:00", "search_now": "1"})
    instant = datetime.fromisoformat(instant_from_results(response))
    assert before <= instant <= datetime.now(timezone.utc)


@pytest.mark.parametrize('zone', ['America/Vancouver', 'UTC'])
@pytest.mark.parametrize('status', ['ALL', 'AVAILABLE'])
def test_search_context_survives_detail_and_back(client, zone, status):
    query = {'driver_id': '1', 'vehicle_id': '1', 'west': '-123.3450', 'south': '48.455',
             'east': '-123.305', 'north': '48.505', 'status': status,
             'arrival_at': '2026-10-26T19:00:46+00:00', 'arrival_timezone': zone}
    results = client.get('/stations', params=query)
    assert results.status_code == 200
    document = FormDocument(results.text)
    detail_url = document.links[0]
    assert parse_qs(urlparse(detail_url).query) == {key: [value] for key, value in query.items()}
    markers = json.loads(re.search(r'id="map-data">(.*?)</script>', results.text, re.S).group(1))
    assert markers[0]['url'] == detail_url
    detail = client.get(detail_url)
    assert detail.status_code == 200
    back = FormDocument(detail.text).back_url
    assert parse_qs(urlparse(back).query) == parse_qs(urlparse(detail_url).query)
    restored = client.get(back)
    assert restored.status_code == 200
    restored_document = FormDocument(restored.text)
    for key in ('west', 'south', 'east', 'north'):
        assert restored_document.inputs[key]['value'] == query[key]
    for name in ('driver_id', 'vehicle_id', 'status', 'arrival_timezone'):
        select = re.search(rf'<select[^>]*name="{name}"[^>]*>(.*?)</select>', restored.text, re.S).group(1)
        assert re.search(rf'value="{query[name]}"[^>]*selected', select)
    assert instant_from_results(restored) == query['arrival_at']


def test_search_now_round_trip_keeps_resolved_instant(client):
    results = client.get('/stations', params={'driver_id': 1, 'vehicle_id': 1, 'search_now': '1'})
    instant = instant_from_results(results)
    detail_url = FormDocument(results.text).links[0]
    assert 'search_now' not in parse_qs(urlparse(detail_url).query)
    back = FormDocument(client.get(detail_url).text).back_url
    assert instant_from_results(client.get(back)) == instant


def test_legacy_detail_without_search_filters_uses_defaults(client):
    detail = client.get('/stations/1', params={'driver_id': 1, 'vehicle_id': 1})
    assert detail.status_code == 200
    back = FormDocument(detail.text).back_url
    query = parse_qs(urlparse(back).query)
    assert query['status'] == ['ALL']
    assert query['arrival_timezone'] == ['America/Vancouver']
    assert all(key in query for key in ('west', 'south', 'east', 'north'))
    assert instant_from_results(client.get(back)) == query['arrival_at'][0]


@pytest.mark.parametrize('extra', [{'status': 'BAD'}, {'west': '-120', 'east': '-130'},
                                 {'north': 'invalid'}, {'arrival_timezone': 'BAD'}])
def test_detail_rejects_invalid_search_context(client, extra):
    response = client.get('/stations/1', params={'driver_id': 1, 'vehicle_id': 1, **extra})
    assert response.status_code == 400
