import json
import re
from pathlib import Path

import pytest

from ca.uvic.ecs.csc501.dal.database import Database
from ca.uvic.ecs.csc501.dal.settings import Settings
from ca.uvic.ecs.csc501.dal.scripts.validate_db import validate_database


def test_matched_sample_is_portable_preserves_sources_and_refuses_overwrite(tmp_path, sample_sources):
    from ca.uvic.ecs.csc501.dal.scripts.import_sample import build_sample
    root = tmp_path / 'sample'
    build_sample(root, *sample_sources)
    db = Database(Settings(root))
    assert validate_database(db) == []
    from ca.uvic.ecs.csc501.dal.unit_of_work import SqlAlchemyUnitOfWork
    with SqlAlchemyUnitOfWork(db) as work:
        stations = work.stations.list()
        assert len(stations) == 20
        assert all(s.station.owner_id is None for s in stations)
        assert all(s.station.city for s in stations)
        assert all(s.station.latitude > 49 for s in stations)
        assert all(p.power_kw is None for s in stations for p in s.ports)
        names = {c.name for c in work.catalog.connectors()}
        assert {'J1772COMBO', 'CCS (Type 1)', 'J1772', 'Type 1 (J1772)'} <= names
        assert work.drivers.list() and work.vehicles.list() and work.memberships.list()
    manifest = json.loads((root / 'source_manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['stations']) == 20
    assert all(str(s['nlr']['ID']) == s['ocm']['DataProvidersReference'] for s in manifest['stations'])
    before = db.settings.database_path.read_bytes()
    with pytest.raises(FileExistsError):
        build_sample(root, *sample_sources)
    assert db.settings.database_path.read_bytes() == before
    db.engine.dispose()


def test_sample_initial_search_and_cross_id_aliases(tmp_path, sample_sources):
    from ca.uvic.ecs.csc501.dal.scripts.import_sample import build_sample
    from ca.uvic.ecs.csc501.main import create_app
    from fastapi.testclient import TestClient
    root = tmp_path / 'sample'
    build_sample(root, *sample_sources)
    db = Database(Settings(root))
    with TestClient(create_app(db)) as client:
        home = client.get('/')
        assert home.status_code == 200 and 'value="-123.5"' not in home.text
        page = client.get('/stations', params={'driver_id': 1, 'vehicle_id': 1, 'arrival_at': '2026-11-02T19:00:00Z'})
        assert page.status_code == 200
        assert 'BC Hydro - North Vancouver' in page.text
        markers = json.loads(re.search(r'<script[^>]*id="map-data"[^>]*>(.*?)</script>', page.text, re.S)[1])
        assert len(markers) == 20
        assert all(float(m['latitude']) > 49 for m in markers)
        services = client.app.state.services
        bounds = services.search_bounds()
        result = services.search(1, 1, '2026-11-02T19:00:00Z', bounds)
        compatible = [x for x in result['results'] if x['checks']['connector']['status'] == 'PASS']
        assert compatible
        assert result['results'][0]['checks']['payment']['status'] == 'PASS'
        visitor = services.detail(1, 2, 1, '2026-11-02T19:00:00Z')
        assert visitor['checks']['payment']['status'] == 'UNKNOWN'
        # Source 329666 has a complete 08:00-17:00 local schedule.
        daytime = services.detail(5, 1, 2, '2026-11-02T19:00:00Z')
        night = services.detail(5, 1, 2, '2026-11-03T06:00:00Z')
        assert daytime['checks']['opening']['status'] == 'PASS'
        assert night['checks']['opening']['status'] == 'FAIL'
        assert night['overall_status'] == 'UNAVAILABLE'
        # Raw NLR codes do not become invented facility class allowances.
        assert all(x['overall_status'] != 'AVAILABLE' for x in result['results'])
        original = services.get_vehicle(1)
        chademo = next(x['connector_type_id'] for x in services.catalog()['connectors'] if x['name'] == 'CHADEMO')
        services.save_vehicle({**original, 'accepted_connector_ids': [chademo]}, 1)
        changed = services.search(1, 1, '2026-11-02T19:00:00Z', bounds)
        assert [x['checks']['connector']['status'] for x in result['results']] != [x['checks']['connector']['status'] for x in changed['results']]
    db.engine.dispose()
