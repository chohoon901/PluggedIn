"""Deterministic evaluation using only supplied domain snapshots and one instant."""
from datetime import datetime
from collections.abc import Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from ..contracts.errors import InputError
from ..contracts.models import StationSnapshot, VehicleSnapshot
from ..contracts.evaluation import (
    CheckStatus, OverallStatus, ReasonCode, Reason, CheckResult, EvaluationResult, EvaluationPolicy,
)
from ..membership import Membership
from ..port import Port


def aggregate_checks(statuses: Iterable[CheckStatus]) -> OverallStatus:
    statuses = tuple(statuses)
    if CheckStatus.FAIL in statuses:
        return OverallStatus.UNAVAILABLE
    if CheckStatus.UNKNOWN in statuses:
        return OverallStatus.NEEDS_REVIEW
    return OverallStatus.AVAILABLE


def _result(status, code, message, evidence):
    return CheckResult(status, (Reason(code, message),), evidence)


def _combine(results: list[CheckResult], evidence: dict) -> CheckResult:
    overall = aggregate_checks(result.status for result in results)
    status = {OverallStatus.AVAILABLE: CheckStatus.PASS, OverallStatus.UNAVAILABLE: CheckStatus.FAIL,
              OverallStatus.NEEDS_REVIEW: CheckStatus.UNKNOWN}[overall]
    return CheckResult(status, tuple(reason for result in results for reason in result.reasons), evidence)


def _normalized(value):
    return ' '.join((value or '').split()).upper()


def _local_arrival(snapshot: StationSnapshot, arrival_at: datetime):
    if not snapshot.metadata.timezone:
        return None
    try:
        return arrival_at.astimezone(ZoneInfo(snapshot.metadata.timezone))
    except (ZoneInfoNotFoundError, ValueError, OverflowError):
        return None


def check_opening(snapshot: StationSnapshot, arrival_at: datetime) -> CheckResult:
    local = _local_arrival(snapshot, arrival_at)
    state = _normalized(snapshot.station.status)
    evidence = {'facility_status': snapshot.station.status, 'timezone': snapshot.metadata.timezone,
                'local_arrival_at': local.isoformat() if local else None,
                'hours_completeness': snapshot.metadata.hours_completeness,
                'operating_periods': [{'day': p.day, 'open_time': str(p.open_time), 'close_time': str(p.close_time)}
                                      for p in snapshot.operating_periods]}
    if state == 'INACTIVE':
        return _result(CheckStatus.FAIL, ReasonCode.CLOSED, 'The facility is recorded as closed.', evidence)
    if local is None:
        return _result(CheckStatus.UNKNOWN, ReasonCode.TIMEZONE_UNKNOWN, 'The local time at the facility cannot be determined.', evidence)
    if not snapshot.operating_periods or snapshot.metadata.hours_completeness != 'COMPLETE':
        hours = _result(CheckStatus.UNKNOWN, ReasonCode.HOURS_UNKNOWN, 'Operating hours are incomplete and need verification.', evidence)
    elif any(period.contains(local) for period in snapshot.operating_periods):
        hours = _result(CheckStatus.PASS, ReasonCode.OPEN, 'The arrival time is within the recorded operating hours.', evidence)
    else:
        hours = _result(CheckStatus.FAIL, ReasonCode.CLOSED, 'The arrival time is outside the recorded operating hours.', evidence)
    if state == 'ACTIVE':
        return hours
    facility = _result(CheckStatus.UNKNOWN, ReasonCode.FACILITY_STATUS_UNKNOWN,
                       'The operating status of the facility cannot be confirmed.', evidence)
    return _combine([hours, facility], evidence)


def check_access(snapshot: StationSnapshot, vehicle: VehicleSnapshot) -> CheckResult:
    station = snapshot.station
    restriction = _normalized(station.access_restriction)
    vehicle_class = _normalized(vehicle.vehicle.vehicle_class)
    maximum = _normalized(station.max_vehicle_class)
    evidence = {'access_restriction': station.access_restriction, 'vehicle_class': vehicle.vehicle.vehicle_class,
                'max_vehicle_class': station.max_vehicle_class, 'has_truck_parking': station.has_truck_parking,
                'unconfirmed_fields': list(snapshot.metadata.unconfirmed_fields)}
    if restriction == 'PUBLIC':
        eligibility = _result(CheckStatus.PASS, ReasonCode.ACCESS_PUBLIC, 'The facility is recorded as open to the public.', evidence)
    elif restriction in ('NO PUBLIC ACCESS', 'CLOSED TO PUBLIC'):
        eligibility = _result(CheckStatus.FAIL, ReasonCode.ACCESS_DENIED, 'The facility does not allow public access.', evidence)
    else:
        eligibility = _result(CheckStatus.UNKNOWN, ReasonCode.ACCESS_RESTRICTED_UNKNOWN,
                              'This information does not confirm eligibility for customer, fleet, or other restricted access.', evidence)
    order = {'CAR': 0, 'VAN': 1, 'MEDIUM_TRUCK': 2, 'HEAVY_TRUCK': 3}
    if vehicle_class not in order or maximum not in (*order, 'ALL'):
        size = _result(CheckStatus.UNKNOWN, ReasonCode.VEHICLE_CLASS_UNKNOWN, 'The vehicle class or facility class limit needs verification.', evidence)
    elif maximum != 'ALL' and order[vehicle_class] > order[maximum]:
        size = _result(CheckStatus.FAIL, ReasonCode.VEHICLE_TOO_LARGE, 'The vehicle exceeds the maximum class recorded for the facility.', evidence)
    else:
        size = CheckResult(CheckStatus.PASS, (), evidence)
    checks = [eligibility, size]
    if vehicle_class in ('MEDIUM_TRUCK','HEAVY_TRUCK'):
        checks.append(_result(CheckStatus.UNKNOWN, ReasonCode.TRUCK_CLEARANCE_UNKNOWN,
                              'Recorded truck parking does not guarantee height, turning, or entry clearance at the charging bay.', evidence))
    return _combine(checks, evidence)


def check_connector(snapshot: StationSnapshot, vehicle: VehicleSnapshot, port: Port | None) -> CheckResult:
    evidence = {'port_id': port.port_id if port else None,
                'connector_type_id': port.connector_type_id if port else None,
                'current_type': port.current_type if port else None,
                'accepted_connector_ids': list(vehicle.accepted_connector_ids),
                'ports_completeness': snapshot.metadata.ports_completeness}
    if port is None:
        return _result(CheckStatus.UNKNOWN, ReasonCode.PORTS_UNKNOWN, 'The port list is missing or incomplete, so unverified connection options remain.', evidence)
    if not vehicle.accepted_connector_ids:
        return _result(CheckStatus.UNKNOWN, ReasonCode.CONNECTOR_UNKNOWN, 'The vehicle has no recorded accepted connectors.', evidence)
    if not vehicle.accepts(port.connector_type_id):
        return _result(CheckStatus.FAIL, ReasonCode.DIRECT_INCOMPATIBLE, 'This port does not directly match a connector registered for the vehicle.', evidence)
    connector = next((c for c in snapshot.connector_types if c.connector_type_id == port.connector_type_id), None)
    name = _normalized(connector.name if connector else None)
    evidence['connector_name'] = connector.name if connector else None
    expected = {'J1772': 'AC', 'CCS1': 'DC', 'CHADEMO': 'DC'}.get(name)
    if expected is None or port.current_type != expected:
        return _result(CheckStatus.UNKNOWN, ReasonCode.CONNECTOR_UNKNOWN,
                       'The connector matches, but the current type or additional vehicle connection requirements cannot be verified.', evidence)
    return _result(CheckStatus.PASS, ReasonCode.DIRECT_COMPATIBLE, 'The registered connector and verified current type support a direct connection.', evidence)


def check_payment(snapshot: StationSnapshot, memberships: list[Membership], arrival_at: datetime,
                  driver_id: int = 1) -> CheckResult:
    station = snapshot.station
    local = _local_arrival(snapshot, arrival_at)
    relevant = [m for m in memberships if m.driver_id == driver_id and m.network_id == station.network_id]
    confirmed_guest = 'accepts_guest_payment' not in snapshot.metadata.unconfirmed_fields
    evidence = {'driver_id': driver_id, 'network_id': station.network_id,
                'accepts_guest_payment': station.accepts_guest_payment, 'guest_payment_confirmed': confirmed_guest,
                'local_arrival_date': local.date().isoformat() if local else None,
                'memberships': [{'membership_id': m.membership_id, 'network_id': m.network_id,
                                 'start_date': m.start_date.isoformat(), 'end_date': m.end_date.isoformat() if m.end_date else None}
                                for m in relevant]}
    if local and any(m.is_active_on(local.date()) for m in relevant):
        return _result(CheckStatus.PASS, ReasonCode.MEMBERSHIP_ACCEPTED, 'The selected driver has a membership for this network that is valid on the local arrival date.', evidence)
    if confirmed_guest and station.accepts_guest_payment:
        return _result(CheckStatus.PASS, ReasonCode.GUEST_PAYMENT_ACCEPTED, 'Guest payment without a membership is confirmed as accepted.', evidence)
    if not confirmed_guest or station.network_id is None or (local is None and relevant):
        return _result(CheckStatus.UNKNOWN, ReasonCode.PAYMENT_UNKNOWN, 'The network, local date, or guest payment information needs verification.', evidence)
    return _result(CheckStatus.FAIL, ReasonCode.NO_PAYMENT_OPTION, 'There is no valid membership for this network, and guest payment is not accepted.', evidence)


def _port_priority(port):
    return (port.power_kw is None, -(port.power_kw or 0), port.port_id or 0)


def evaluate_station(station: StationSnapshot, vehicle: VehicleSnapshot, memberships: list[Membership],
                     arrival_at: datetime, policy: EvaluationPolicy | None = None, *, driver_id: int = 1) -> EvaluationResult:
    if not isinstance(arrival_at, datetime) or arrival_at.tzinfo is None or arrival_at.utcoffset() is None:
        raise InputError('The arrival time must include UTC or a time zone offset.', {'arrival_at': 'Enter a time with a time zone offset.'})
    common = {'opening': check_opening(station, arrival_at), 'access': check_access(station, vehicle),
              'payment': check_payment(station, memberships, arrival_at, driver_id)}
    ports = sorted(station.ports, key=_port_priority)
    candidates = []
    compatible = []
    for port in ports:
        connector = check_connector(station, vehicle, port)
        if connector.status == CheckStatus.PASS:
            compatible.append(port.port_id)
        checks = {**common, 'connector': connector}
        candidates.append((aggregate_checks(check.status for check in checks.values()), port, checks))
    if not ports or station.metadata.ports_completeness != 'COMPLETE':
        checks = {**common, 'connector': check_connector(station, vehicle, None)}
        candidates.append((aggregate_checks(check.status for check in checks.values()), None, checks))
    rank = {OverallStatus.AVAILABLE: 0, OverallStatus.NEEDS_REVIEW: 1, OverallStatus.UNAVAILABLE: 2}
    connector_rank = {CheckStatus.PASS: 0, CheckStatus.UNKNOWN: 1, CheckStatus.FAIL: 2}
    # 공통 조건 때문에 모든 후보가 실패해도 직접 연결 가능한 포트를 대표로 설명합니다.
    # 같은 연결 상태 안에서는 이미 정렬된 출력·번호 우선순위를 유지합니다.
    overall, selected, checks = min(candidates, key=lambda candidate: (rank[candidate[0]], connector_rank[candidate[2]['connector'].status]))
    power = min(selected.power_kw, vehicle.vehicle.max_charge_kw) if selected and selected.power_kw is not None and vehicle.vehicle.max_charge_kw is not None else None
    warnings = () if power is not None else (Reason(ReasonCode.POWER_UNKNOWN, 'The power limit is unknown because the port or vehicle power limit is missing.'),)
    if any(field.rsplit('.', 1)[-1] == 'quantity' for field in station.metadata.unconfirmed_fields):
        warnings += (Reason(ReasonCode.PORTS_UNKNOWN, 'The port quantity is unverified. The database default does not confirm the actual number of ports.'),)
    return EvaluationResult(station.station.station_id, driver_id, vehicle.vehicle.vehicle_id, arrival_at,
                            checks, overall, tuple(compatible), selected.port_id if selected else None, power, warnings)
