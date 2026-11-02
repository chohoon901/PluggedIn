"""English website messages are produced by real validation and evaluation paths."""
from contextlib import nullcontext
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from ca.uvic.ecs.csc501.cmn.application.services import ApplicationService, parse_arrival
from ca.uvic.ecs.csc501.cmn.connector_type import ConnectorType
from ca.uvic.ecs.csc501.cmn.contracts.errors import AppError
from ca.uvic.ecs.csc501.cmn.contracts.models import StationMetadata, StationSnapshot, VehicleSnapshot
from ca.uvic.ecs.csc501.cmn.driver import Driver
from ca.uvic.ecs.csc501.cmn.membership import Membership
from ca.uvic.ecs.csc501.cmn.operating_period import OperatingPeriod
from ca.uvic.ecs.csc501.cmn.port import Port
from ca.uvic.ecs.csc501.cmn.services import evaluation
from ca.uvic.ecs.csc501.cmn.station import Station
from ca.uvic.ecs.csc501.cmn.value_objects.daily_time import DailyTime
from ca.uvic.ecs.csc501.cmn.vehicle import Vehicle
from ca.uvic.ecs.csc501.dal.metadata import normalize_stations


@pytest.fixture
def scenario():
    station = Station(1, Decimal('48.46'), Decimal('-123.31'), 'Station', None, 'Victoria', 'BC',
                      'ACTIVE', 'public', False, 'VAN', False, 1, 1, 1)
    snapshot = StationSnapshot(station, (Port(1, 1, 1, 1, Decimal('150'), 'DC', 1),),
                               (OperatingPeriod(1, 1, 'Mon', DailyTime(0), DailyTime(86400)),),
                               (ConnectorType(1, 'CCS1'),), (),
                               StationMetadata('America/Vancouver', 'COMPLETE', 'COMPLETE', 'COMPLETE'))
    vehicle = VehicleSnapshot(Vehicle(1, 'DEMO0000000000001', vehicle_class='VAN',
                                      max_charge_kw=Decimal('100')), (1,))
    memberships = [Membership(1, 1, 1, date(2026, 1, 1))]
    return snapshot, vehicle, memberships, datetime(2026, 10, 26, 19, tzinfo=timezone.utc)


def assert_english(message):
    assert message and message.isascii(), message
    assert any(character.isalpha() for character in message), message


def test_real_evaluation_paths_explain_pass_failure_and_uncertainty_in_english(scenario):
    snapshot, vehicle, memberships, arrival = scenario
    changed = lambda **values: replace(snapshot, station=replace(snapshot.station, **values))
    metadata = lambda **values: replace(snapshot, metadata=replace(snapshot.metadata, **values))
    checks = [
        evaluation.check_opening(snapshot, arrival),
        evaluation.check_opening(changed(status='INACTIVE'), arrival),
        evaluation.check_opening(metadata(timezone=None), arrival),
        evaluation.check_opening(metadata(hours_completeness='PARTIAL'), arrival),
        evaluation.check_opening(snapshot, arrival.replace(day=27)),
        evaluation.check_opening(changed(status=None), arrival),
        evaluation.check_access(snapshot, vehicle),
        evaluation.check_access(changed(access_restriction='no public access'), vehicle),
        evaluation.check_access(changed(access_restriction='customers only'), vehicle),
        evaluation.check_access(changed(max_vehicle_class=None), vehicle),
        evaluation.check_access(changed(max_vehicle_class='CAR'), vehicle),
        evaluation.check_access(changed(max_vehicle_class='ALL'),
                                replace(vehicle, vehicle=replace(vehicle.vehicle, vehicle_class='HEAVY_TRUCK'))),
        evaluation.check_connector(snapshot, vehicle, None),
        evaluation.check_connector(snapshot, replace(vehicle, accepted_connector_ids=()), snapshot.ports[0]),
        evaluation.check_connector(snapshot, replace(vehicle, accepted_connector_ids=(2,)), snapshot.ports[0]),
        evaluation.check_connector(snapshot, vehicle, replace(snapshot.ports[0], current_type=None)),
        evaluation.check_connector(snapshot, vehicle, snapshot.ports[0]),
        evaluation.check_payment(snapshot, memberships, arrival),
        evaluation.check_payment(changed(accepts_guest_payment=True), [], arrival),
        evaluation.check_payment(changed(network_id=None), [], arrival),
        evaluation.check_payment(snapshot, [], arrival),
    ]
    assert {check.status for check in checks} == {'PASS', 'FAIL', 'UNKNOWN'}
    for check in checks:
        for reason in check.reasons:
            assert_english(reason.message)


def test_real_evaluation_warnings_remain_english_without_hiding_unknown_evidence(scenario):
    snapshot, vehicle, memberships, arrival = scenario
    snapshot = replace(snapshot, metadata=replace(snapshot.metadata, unconfirmed_fields=('quantity',)))
    vehicle = replace(vehicle, vehicle=replace(vehicle.vehicle, max_charge_kw=None))
    result = evaluation.evaluate_station(snapshot, vehicle, memberships, arrival)
    assert result.overall_status == 'AVAILABLE'
    assert {reason.code for reason in result.warnings} == {'POWER_UNKNOWN', 'PORTS_UNKNOWN'}
    for reason in result.warnings:
        assert_english(reason.message)


@pytest.fixture
def service(scenario):
    snapshot, vehicle, _, _ = scenario
    driver = Driver(1, 'TEST-LICENCE', '사용자 이름')
    uow = SimpleNamespace(
        drivers=SimpleNamespace(get=lambda identifier: driver if identifier == 1 else None),
        vehicles=SimpleNamespace(get=lambda identifier: vehicle if identifier == 1 else None),
        memberships=SimpleNamespace(get=lambda identifier: None, list=lambda identifier: []),
        stations=SimpleNamespace(get=lambda identifier: None),
        catalog=SimpleNamespace(connectors=lambda: snapshot.connector_types, networks=lambda: []),
    )
    return ApplicationService(lambda: nullcontext(uow), lambda: True)


@pytest.mark.parametrize('invalid_request', [
    lambda service: service.save_driver({}),
    lambda service: service.save_driver({'licence_number': 123}),
    lambda service: service.save_driver({'licence_number': 'X' * 31}),
    lambda service: service.get_driver('invalid'),
    lambda service: service.get_driver(2),
    lambda service: service.get_vehicle(2),
    lambda service: service.get_membership(2),
    lambda service: service.save_vehicle({'vehicle_class': 'BUS'}),
    lambda service: service.save_vehicle({'accepted_connector_ids': []}),
    lambda service: service.save_vehicle({'accepted_connector_ids': [2]}),
    lambda service: service.save_vehicle({'accepted_connector_ids': [1], 'vin': 'SHORT'}),
    lambda service: service.save_vehicle({'accepted_connector_ids': [1], 'vin': 'DEMO0000000000001', 'range_km': '-1'}),
    lambda service: service.save_vehicle({'accepted_connector_ids': [1], 'vin': 'DEMO0000000000001', 'max_charge_kw': 'bad'}),
    lambda service: service.save_membership({'driver_id': 1, 'network_id': 1}),
    lambda service: service.save_membership({'driver_id': 1, 'network_id': 1, 'start_date': 'bad'}),
    lambda service: service.save_membership({'driver_id': 1, 'network_id': 1, 'start_date': '2026-10-26', 'end_date': '2026-10-25'}),
    lambda service: service.save_membership({'driver_id': 1, 'network_id': 1, 'start_date': '2026-10-26'}),
    lambda service: service.search(1, 1, '2026-10-26T19:00:00Z', {}, 'invalid'),
    lambda service: service.search(1, 1, '2026-10-26T19:00:00Z', {}),
    lambda service: service.detail(2, 1, 1, '2026-10-26T19:00:00Z'),
    lambda service: parse_arrival('2026-10-26T19:00'),
])
def test_invalid_service_requests_return_english_errors_and_field_feedback(service, invalid_request):
    with pytest.raises(AppError) as error:
        invalid_request(service)
    assert_english(error.value.message)
    for message in error.value.field_errors.values():
        assert_english(message)


def test_generated_unknown_source_label_is_english_and_preserves_user_source():
    values = normalize_stations({'1': {}, '2': {'sourceLabel': '사용자 출처'}})
    assert_english(values['1']['sourceLabel'])
    assert values['2']['sourceLabel'] == '사용자 출처'
    assert_english(StationMetadata().source_label)
