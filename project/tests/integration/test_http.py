"""Real DB/HTTP boundary tests: no browser or JavaScript is needed."""
import json
import re

import pytest
from fastapi.testclient import TestClient


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


def test_api_crud_normalizes_and_rejects_duplicate(client):
    result = client.post('/api/v1/drivers', json={'licence_number': '  NEW-001  ', 'name': 'Kim', 'carrier_name': ''})
    assert result.status_code == 201
    driver = result.json()
    assert driver['licence_number'] == 'NEW-001'
    assert driver['carrier_name'] is None
    assert client.get(f"/api/v1/drivers/{driver['driver_id']}").json()['name'] == 'Kim'
    assert client.post('/api/v1/drivers', json={'licence_number': 'NEW-001'}).status_code == 409
    updated = client.put(f"/api/v1/drivers/{driver['driver_id']}", json={'licence_number': 'NEW-002'})
    assert updated.status_code == 200 and updated.json()['name'] is None
    assert client.delete(f"/api/v1/drivers/{driver['driver_id']}").status_code == 204
    assert client.get(f"/api/v1/drivers/{driver['driver_id']}").status_code == 404


@pytest.mark.parametrize('path,data', [
    ('drivers', {'licence_number': ''}),
    ('drivers', {'licence_number': 'L', 'driver_id': 100}),
    ('vehicles', {'vin': 'short', 'accepted_connector_ids': [1]}),
    ('vehicles', {'vin': 'NEW00000000000001', 'accepted_connector_ids': []}),
    ('vehicles', {'vin': 'NEW00000000000001', 'accepted_connector_ids': [1], 'max_charge_kw': 0}),
    ('memberships', {'driver_id': 1, 'network_id': 1, 'start_date': '2026-03-02', 'end_date': '2026-03-01'}),
    ('stations/search', {'driver_id': 1, 'vehicle_id': 1, 'arrival_at': '2026-10-26T19:00:00', 'bbox': {'west': -123.5, 'east': -123.2, 'south': 48.35, 'north': 48.6}}),
    ('stations/search', {'driver_id': 1, 'vehicle_id': 1, 'bbox': {'west': -123.2, 'east': -123.5, 'south': 48.35, 'north': 48.6}}),
])
def test_bad_api_inputs_are_400_envelopes(client, path, data):
    response = client.post('/api/v1/' + path, json=data)
    assert response.status_code == 400
    assert {'code', 'message', 'field_errors'} <= response.json()['error'].keys()


def test_forms_restore_values_and_use_prg(client):
    response = client.post('/drivers', data={'licence_number': '', 'name': '<script>bad()</script>', 'carrier_name': 'My company'})
    assert response.status_code == 400
    assert '&lt;script&gt;bad()&lt;/script&gt;' in response.text
    assert '<script>bad()</script>' not in response.text
    assert 'My company' in response.text
    response = client.post('/drivers', data={'licence_number': 'FORM-001', 'name': 'Form driver'}, follow_redirects=False)
    assert response.status_code == 303 and response.headers['location'] == '/drivers'
    assert 'Form driver' in client.get('/drivers').text
    invalid = client.post('/vehicles', data={'vin': 'short', 'make': 'Remember Me', 'accepted_connector_ids': '1'})
    assert invalid.status_code == 400 and 'Remember Me' in invalid.text
    assert re.search(r'value="1"[^>]*checked', invalid.text)


def test_vehicle_and_membership_api_replace_and_delete(client):
    vehicle = client.post('/api/v1/vehicles', json={'vin': 'NEW00000000000001', 'accepted_connector_ids': [2, 1, 2], 'make': 'New'} )
    assert vehicle.status_code == 201
    item = vehicle.json()
    assert item['accepted_connector_ids'] == [1, 2]
    assert client.put(f"/api/v1/vehicles/{item['vehicle_id']}", json={'vin': item['vin'], 'accepted_connector_ids': [2]}).json()['accepted_connector_ids'] == [2]
    assert client.delete(f"/api/v1/vehicles/{item['vehicle_id']}").status_code == 204
    membership = client.post('/api/v1/memberships', json={'driver_id': 2, 'network_id': 1, 'start_date': '2026-01-01'})
    assert membership.status_code == 201
    mid = membership.json()['membership_id']
    assert client.put(f'/api/v1/memberships/{mid}', json={'driver_id': 2, 'network_id': 1, 'start_date': '2026-01-02', 'end_date': '2026-12-31'}).status_code == 200
    assert client.delete(f'/api/v1/memberships/{mid}').status_code == 204


def test_ssr_search_has_results_reasons_and_fixed_detail_instant(client):
    query = {'driver_id': 1, 'vehicle_id': 1, 'arrival_at': '2026-10-26T19:00:00Z'}
    response = client.get('/stations', params=query)
    assert response.status_code == 200
    assert all(name in response.text for name in ['Demo A', 'Demo B', 'Demo C', 'Demo D', 'Demo E'])
    assert all(label in response.text for label in ['Available', 'Needs review', 'Unavailable'])
    assert 'DIRECT_INCOMPATIBLE' in response.text
    raw = re.search(r'<script type="application/json" id="map-data">(.*?)</script>', response.text, re.S).group(1)
    assert len(json.loads(raw)) == 5
    detail = client.get('/stations/1', params=query)
    assert detail.status_code == 200
    assert '2026-10-26T19:00:00' in detail.text
    assert 'destination=48.46%2C-123.31' in detail.text
    assert 'Local project demo data' in detail.text
    assert 'Update date unknown' in detail.text


def test_search_apis_match_ssr_and_unready_health_is_503(client, tmp_path):
    payload = {'driver_id': 1, 'vehicle_id': 1, 'arrival_at': '2026-10-26T19:00:00Z', 'bbox': {'west': -123.5, 'east': -123.2, 'south': 48.35, 'north': 48.6}}
    result = client.post('/api/v1/stations/search', json=payload)
    assert result.status_code == 200
    assert result.json()['counts'] == {'AVAILABLE': 3, 'NEEDS_REVIEW': 1, 'UNAVAILABLE': 1}
    assert client.post('/api/v1/stations/1/evaluate', json={k: v for k, v in payload.items() if k != 'bbox'}).json()['overall_status'] == 'AVAILABLE'
    assert client.get('/stations', params={'driver_id': 'bad', 'vehicle_id': 1}).status_code == 400
    assert client.get('/stations', params={'driver_id': 9999, 'vehicle_id': 1}).status_code == 404
    assert client.get('/api/v1/health').status_code == 200
    from ca.uvic.ecs.csc501.dal.settings import Settings
    from ca.uvic.ecs.csc501.dal.database import Database
    from ca.uvic.ecs.csc501.main import create_app
    db = Database(Settings(dal_root=tmp_path / 'unready'))
    with TestClient(create_app(db)) as unready:
        response = unready.get('/api/v1/health')
        assert response.status_code == 503 and response.json()['error']['code']
        assert unready.get('/drivers').headers['content-type'].startswith('text/html')
    db.engine.dispose()


@pytest.mark.parametrize('path', ['/', '/drivers', '/drivers/new', '/drivers/1/edit', '/vehicles', '/vehicles/new', '/vehicles/1/edit', '/memberships', '/memberships?driver_id=', '/memberships/new', '/memberships/1/edit'])
def test_all_ssr_pages_render_without_script_execution(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert '<main id="main"' in response.text


def test_membership_form_restores_invalid_dates_and_selected_ids(client):
    response = client.post('/memberships', data={'driver_id': '2', 'network_id': '1', 'start_date': '2026-05-02', 'end_date': '2026-05-01'})
    assert response.status_code == 400
    assert 'value="2026-05-02"' in response.text and 'value="2026-05-01"' in response.text
    assert re.search(r'value="2"[^>]*selected', response.text)
    assert re.search(r'value="1"[^>]*selected', response.text)
    assert client.get('/api/v1/memberships?driver_id=2').json()[0]['network_id'] == 2


def test_form_conflict_preserves_values_and_edit_delete_are_real(client):
    duplicate = client.post('/drivers', data={'licence_number': 'DEMO-LIC-001', 'name': 'Keep this name'})
    assert duplicate.status_code == 400 and 'Keep this name' in duplicate.text
    changed = client.post('/drivers/2', data={'licence_number': 'DEMO-LIC-002', 'name': 'Jin changed', 'carrier_name': 'Stored carrier'}, follow_redirects=False)
    assert changed.status_code == 303
    assert client.get('/api/v1/drivers/2').json()['carrier_name'] == 'Stored carrier'
    assert client.get('/drivers/2/delete').status_code == 405
    deleted = client.post('/drivers/2/delete', follow_redirects=False)
    assert deleted.status_code == 303
    assert client.get('/api/v1/memberships?driver_id=2').json() == []


def test_status_filter_counts_and_empty_results_preserve_conditions(client):
    query = {'driver_id': 1, 'vehicle_id': 1, 'arrival_at': '2026-10-26T19:00:00Z', 'status': 'NEEDS_REVIEW'}
    response = client.get('/stations', params=query)
    assert response.status_code == 200
    raw = re.search(r'<script type="application/json" id="map-data">(.*?)</script>', response.text, re.S).group(1)
    assert [item['name'] for item in json.loads(raw)] == ['Demo D']
    query.update(west='-130', east='-129', south='49', north='50')
    empty = client.get('/stations', params=query)
    assert empty.status_code == 200
    assert 'No stations match your search' in empty.text
    assert 'value="-130"' in empty.text


@pytest.mark.parametrize('path', [
    '/', '/drivers', '/drivers/new', '/drivers/1/edit',
    '/vehicles', '/vehicles/new', '/vehicles/1/edit',
    '/memberships', '/memberships/new', '/memberships/1/edit',
    '/stations?driver_id=1&vehicle_id=1&arrival_at=2026-10-26T19%3A00%3A00Z',
    '/stations/1?driver_id=1&vehicle_id=1&arrival_at=2026-10-26T19%3A00%3A00Z',
    '/missing-page',
])
def test_website_renders_english_navigation_labels_and_help(client, path):
    response = client.get(path)
    assert response.status_code in (200, 404)
    assert '<html lang="en">' in response.text
    assert all(label in response.text for label in ['Find charging', 'Drivers', 'Vehicles', 'Memberships'])
    assert not re.search(r'[\uac00-\ud7a3]', response.text)


def test_english_forms_preserve_user_supplied_language(client):
    response = client.post('/drivers', data={'licence_number': 'LANGUAGE-001', 'name': '김민아', 'carrier_name': '사용자 운송사'}, follow_redirects=False)
    assert response.status_code == 303
    page = client.get('/drivers')
    assert '김민아' in page.text and '사용자 운송사' in page.text
    assert 'Registered drivers' in page.text
