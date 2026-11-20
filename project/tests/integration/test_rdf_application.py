import pytest
from fastapi.testclient import TestClient

from ca.uvic.ecs.csc501.cmn.application.services import ApplicationService
from ca.uvic.ecs.csc501.cmn.contracts.errors import ConflictError
from ca.uvic.ecs.csc501.dal.database import Database
from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
from ca.uvic.ecs.csc501.dal.settings import Settings


def test_app_only_virtuoso_origin_configures_both_endpoints(monkeypatch):
    monkeypatch.setenv('PLUGGEDIN_VIRTUOSO_ORIGIN', 'http://127.0.0.1:8893/')

    settings = Settings()

    assert settings.sparql_endpoint == 'http://127.0.0.1:8893/sparql'
    assert settings.app_sparql_endpoint == 'http://127.0.0.1:8893/sparql-auth'
from ca.uvic.ecs.csc501.dal.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def application(tmp_path, rdf_store):
    from ca.uvic.ecs.csc501.dal.semantic.unit_of_work import VirtuosoUnitOfWork

    database = Database(Settings(tmp_path))
    init_database(database)
    seed_demo(database)
    graph = rdf_store(database)
    yield (
        ApplicationService(lambda: VirtuosoUnitOfWork(graph), lambda: True),
        ApplicationService(lambda: SqlAlchemyUnitOfWork(database), database.health),
        graph,
    )
    database.engine.dispose()


def test_default_http_application_reads_and_writes_the_rdf_store(application, monkeypatch):
    from ca.uvic.ecs.csc501.dal.semantic.store import VirtuosoStore
    from ca.uvic.ecs.csc501.main import create_app

    _, _, graph = application
    monkeypatch.setattr(VirtuosoStore, 'from_settings', classmethod(lambda cls, settings: graph))

    def unexpected_sqlite(*args, **kwargs):
        pytest.fail('The default application must not open SQLite.')

    monkeypatch.setattr(Database, '__init__', unexpected_sqlite)
    with TestClient(create_app()) as client:
        assert client.get('/api/v1/health').status_code == 200
        assert client.get('/drivers').status_code == 200
        created = client.post('/drivers', data={'licence_number': 'RDF-SSR', 'name': 'RDF driver'},
                              follow_redirects=False)
        assert created.status_code == 303
    with TestClient(create_app()) as client:
        assert 'RDF driver' in client.get('/drivers').text


def test_imported_graph_preserves_profiles_catalogue_and_station_evaluation(application):
    rdf, sqlite, _ = application
    assert rdf.list_drivers() == sqlite.list_drivers()
    assert rdf.list_vehicles() == sqlite.list_vehicles()
    assert rdf.list_memberships() == sqlite.list_memberships()
    assert rdf.catalog() == sqlite.catalog()
    assert rdf.search_bounds() == sqlite.search_bounds()

    arrival = '2026-10-26T19:00:00Z'
    before = sqlite.detail(1, 1, 1, arrival)
    moved = rdf.detail(1, 1, 1, arrival)
    for key in ('station', 'ports', 'operating_periods', 'organizations', 'source'):
        assert moved[key] == before[key]
    assert moved['overall_status'] == before['overall_status']


def test_graph_driver_delete_removes_memberships_without_removing_vehicles(application):
    rdf, _, _ = application
    saved = rdf.save_driver({'licence_number': 'RDF TEST', 'name': '이름 "문자" & \\'})
    rdf.save_membership({'driver_id': saved['driver_id'], 'network_id': 1, 'start_date': '2026-11-01'})
    assert rdf.get_driver(saved['driver_id']) == saved
    assert len(rdf.list_memberships(saved['driver_id'])) == 1

    vehicles = rdf.list_vehicles()
    rdf.delete_driver(saved['driver_id'])
    assert rdf.list_memberships(saved['driver_id']) == []
    assert rdf.list_vehicles() == vehicles


def test_duplicate_vehicle_rolls_back_acceptance_changes(application):
    rdf, _, graph = application
    vehicle = rdf.save_vehicle({'vin': 'RDF00000000000001', 'accepted_connector_ids': [1]})
    version = graph.snapshot
    with pytest.raises(ConflictError):
        rdf.save_vehicle({'vin': rdf.list_vehicles()[0]['vin'], 'accepted_connector_ids': [2]}, vehicle['vehicle_id'])
    assert graph.snapshot is version
    assert rdf.get_vehicle(vehicle['vehicle_id'])['accepted_connector_ids'] == [1]

    updated = rdf.save_vehicle({'vin': vehicle['vin'], 'accepted_connector_ids': [2]}, vehicle['vehicle_id'])
    assert updated['accepted_connector_ids'] == [2]
    assert rdf.get_vehicle(vehicle['vehicle_id']) == updated


def test_stale_unit_of_work_cannot_overwrite_newer_profile_data(application):
    from ca.uvic.ecs.csc501.cmn.domain.driver import Driver
    from ca.uvic.ecs.csc501.dal.semantic.unit_of_work import VirtuosoUnitOfWork

    rdf, _, graph = application
    with VirtuosoUnitOfWork(graph) as first, VirtuosoUnitOfWork(graph) as stale:
        first.drivers.save(Driver(None, 'FIRST', 'First writer'))
        stale.drivers.save(Driver(None, 'STALE', 'Stale writer'))
        first.commit()
        with pytest.raises(ConflictError):
            stale.commit()
    assert {driver['licence_number'] for driver in rdf.list_drivers()} >= {'FIRST'}
    assert all(driver['licence_number'] != 'STALE' for driver in rdf.list_drivers())
