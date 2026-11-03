import pytest
from fastapi.testclient import TestClient

from ca.uvic.ecs.csc501.dal.database import Database
from ca.uvic.ecs.csc501.dal.settings import Settings
from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
from ca.uvic.ecs.csc501.dal.scripts.validate_db import validate_database
from ca.uvic.ecs.csc501.dal.unit_of_work import SqlAlchemyUnitOfWork
from ca.uvic.ecs.csc501.dal.models import StationModel
from ca.uvic.ecs.csc501.cmn.contracts.errors import ConflictError
from ca.uvic.ecs.csc501.main import create_app


def test_null_roles_roundtrip_api_and_html_keep_foreign_keys(tmp_path):
    db = Database(Settings(tmp_path))
    init_database(db)
    seed_demo(db)
    with SqlAlchemyUnitOfWork(db) as work:
        row = work.session.get(StationModel, 1)
        row.owner_id = row.operator_id = None
        work.commit()
    assert validate_database(db) == []
    with SqlAlchemyUnitOfWork(db) as work:
        assert work.stations.get(1).station.owner_id is None
    with pytest.raises(ConflictError):
        with SqlAlchemyUnitOfWork(db) as work:
            work.session.get(StationModel, 1).owner_id = 999
            work.commit()
    with TestClient(create_app(db)) as client:
        payload = {'driver_id': 1, 'vehicle_id': 1, 'arrival_at': '2026-10-26T19:00:00Z'}
        response = client.post('/api/v1/stations/1/evaluate', json=payload)
        assert response.status_code == 200
        assert response.json()['station']['owner_id'] is None
        page = client.get('/stations/1', params=payload)
        assert page.status_code == 200
        assert 'Site owner unknown' in page.text and 'Station operator unknown' in page.text
    db.engine.dispose()
