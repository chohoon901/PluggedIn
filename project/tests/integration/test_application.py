from datetime import datetime, timezone
import importlib

import pytest


def service_module():
    try:
        return importlib.import_module("ca.uvic.ecs.csc501.cmn.application.services")
    except ImportError as exc:
        pytest.fail(f"ApplicationService is not implemented: {exc}")


def test_arrival_requires_explicit_offset():
    module = service_module()
    from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError
    with pytest.raises(InputError):
        module.parse_arrival("2026-10-26T12:00:00")
    assert module.parse_arrival("2026-10-26T19:00:00Z") == datetime(2026, 10, 26, 19, tzinfo=timezone.utc)


@pytest.fixture
def service(tmp_path):
    module = service_module()
    from ca.uvic.ecs.csc501.dal.settings import Settings
    from ca.uvic.ecs.csc501.dal.database import Database
    from ca.uvic.ecs.csc501.dal.unit_of_work import SqlAlchemyUnitOfWork
    from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
    from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
    database = Database(Settings(dal_root=tmp_path / "dal"))
    init_database(database)
    seed_demo(database)
    yield module.ApplicationService(lambda: SqlAlchemyUnitOfWork(database), database.health)
    database.engine.dispose()


BBOX = {"west": -123.5, "south": 48.35, "east": -123.2, "north": 48.6}
ARRIVAL = "2026-10-26T19:00:00Z"


def test_demo_and_membership_changes_recompute_from_database(service):
    result = service.search(1, 1, ARRIVAL, BBOX)
    assert [row["overall_status"] for row in result["results"]] == [
        "AVAILABLE", "AVAILABLE", "UNAVAILABLE", "NEEDS_REVIEW", "AVAILABLE"
    ]
    assert result["results"][0]["power_limit_kw"] == 100
    assert service.detail(1, 2, 1, ARRIVAL)["overall_status"] == "UNAVAILABLE"
    member = service.save_membership({"driver_id": 2, "network_id": 1, "start_date": "2026-01-01"})
    assert service.detail(1, 2, 1, ARRIVAL)["overall_status"] == "AVAILABLE"
    service.delete_membership(member["membership_id"])
    assert service.detail(1, 2, 1, ARRIVAL)["overall_status"] == "UNAVAILABLE"


def test_vehicle_update_and_invalid_connector_do_not_leave_partial_data(service):
    from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError
    vehicle = service.get_vehicle(1)
    vehicle["accepted_connector_ids"] = [2]
    service.save_vehicle(vehicle, 1)
    assert service.detail(3, 1, 1, ARRIVAL)["checks"]["connector"]["status"] == "PASS"
    vehicle["model"] = "must not save"
    vehicle["accepted_connector_ids"] = [9999]
    with pytest.raises(InputError):
        service.save_vehicle(vehicle, 1)
    assert service.get_vehicle(1)["model"] == "Van"
    assert service.get_vehicle(1)["accepted_connector_ids"] == [2]


def test_crud_preserves_every_optional_field_and_cascades(service):
    driver = service.save_driver({"licence_number": " TEST-LIC ", "name": "수빈", "carrier_name": "테스트 운송"})
    assert service.get_driver(driver["driver_id"])["licence_number"] == "TEST-LIC"
    member = service.save_membership({"driver_id": driver["driver_id"], "network_id": 1, "start_date": "2026-01-01", "end_date": "2026-12-31"})
    assert member["end_date"] == "2026-12-31"
    service.delete_driver(driver["driver_id"])
    assert service.list_memberships(driver["driver_id"]) == []
    assert len(service.list_vehicles()) == 1


def test_invalid_inputs_and_missing_ids_have_domain_errors(service):
    from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError, NotFoundError, ConflictError
    with pytest.raises(NotFoundError):
        service.get_driver(9999)
    with pytest.raises(InputError):
        service.save_vehicle({"vin": "bad", "accepted_connector_ids": [1]})
    with pytest.raises(InputError):
        service.search(1, 1, ARRIVAL, {**BBOX, "east": -124})
    with pytest.raises(ConflictError):
        service.save_driver({"licence_number": "DEMO-LIC-001"})
    assert len(service.list_drivers()) == 2


def test_search_preserves_exact_instant_and_filters(service):
    result = service.search(1, 1, "2026-10-27T05:00:00Z", BBOX, "UNAVAILABLE")
    assert [r["station_id"] for r in result["results"]] == [2, 3]
    detail = service.detail(2, 1, 1, result["arrival_at"])
    assert detail["arrival_at"] == result["arrival_at"]
    assert detail["checks"]["opening"]["status"] == "FAIL"


def test_new_application_instance_reads_saved_database_after_restart(tmp_path):
    from ca.uvic.ecs.csc501.dal.settings import Settings
    from ca.uvic.ecs.csc501.dal.database import Database
    from ca.uvic.ecs.csc501.dal.unit_of_work import SqlAlchemyUnitOfWork
    from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
    from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
    from ca.uvic.ecs.csc501.cmn.application.services import ApplicationService
    settings = Settings(dal_root=tmp_path / "dal")
    first = Database(settings)
    init_database(first)
    seed_demo(first)
    service = ApplicationService(lambda: SqlAlchemyUnitOfWork(first), first.health)
    saved = service.save_driver({"licence_number": "RESTART-01", "name": "재시작 보존", "carrier_name": "운송사"})
    first.engine.dispose()
    second = Database(settings)
    init_database(second)
    restarted = ApplicationService(lambda: SqlAlchemyUnitOfWork(second), second.health)
    assert restarted.get_driver(saved["driver_id"]) == saved
    second.engine.dispose()


def test_unrepresentable_sqlite_integers_are_input_errors_and_update_is_atomic(service):
    from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError
    with pytest.raises(InputError):
        service.get_driver(9223372036854775808)
    original = service.get_vehicle(1)
    invalid = {**original, "model": "must not change", "range_km": 9223372036854775808, "accepted_connector_ids": [2]}
    with pytest.raises(InputError):
        service.save_vehicle(invalid, 1)
    assert service.get_vehicle(1) == original
