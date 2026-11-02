"""SSR와 JSON API가 공유하는 저장·조회·충전 판정 use case."""
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Callable

from ..contracts.errors import InputError, NotFoundError
from ..contracts.repositories import UnitOfWork
from ..driver import Driver
from ..membership import Membership
from ..vehicle import Vehicle
from ..value_objects.daily_time import DailyTime
from ..services.evaluation import evaluate_station


def current_instant() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_arrival(value: str | datetime | None, now: datetime | None = None) -> datetime:
    if value is None or value == "":
        return now if now is not None else datetime.now(timezone.utc)
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError
        return instant.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        raise InputError("Include a time zone offset such as Z or +00:00 in the arrival time.", {"arrival_at": "Enter an ISO date and time with a time zone offset."}) from None


def _plain(value):
    if isinstance(value, DailyTime):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    return value


def _id(value, field="id") -> int:
    try:
        if isinstance(value, bool) or not str(value).isdigit() or not 0 < int(value) <= 9223372036854775807:
            raise ValueError
        return int(value)
    except (TypeError, ValueError):
        raise InputError("Select a valid registered item.", {field: "A positive integer ID is required."}) from None


def _text(data: dict, name: str, limit: int, required=False):
    value = data.get(name)
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise InputError("Check the text input.", {name: "Enter text."})
    value = value.strip()
    if required and not value:
        raise InputError("Check the required fields.", {name: "This field is required."})
    if len(value) > limit:
        raise InputError("Check the input length.", {name: f"Enter no more than {limit} characters."})
    return value or None


def _number(data: dict, name: str, *, integer=False):
    value = data.get(name)
    if value is None or value == "":
        return None
    try:
        if isinstance(value, bool):
            raise ValueError
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0:
            raise ValueError
        if integer:
            if number != number.to_integral_value() or number > 9223372036854775807:
                raise ValueError
            return int(number)
        number = number.quantize(Decimal("0.1"))
        if number <= 0 or number > Decimal("99999.9"):
            raise ValueError
        return number
    except (ValueError, InvalidOperation):
        raise InputError("Check the numeric input.", {name: "Enter a positive integer." if integer else "Enter a valid kW value greater than zero."}) from None


def _day(data: dict, name: str, required=False):
    value = data.get(name)
    if value is None or value == "":
        if required:
            raise InputError("Enter a date.", {name: "This date is required."})
        return None
    try:
        if type(value) is date:
            return value
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise InputError("Check the date format.", {name: "Use the YYYY-MM-DD format."}) from None


def _found(value, label):
    if value is None:
        raise NotFoundError(f"The registered {label} could not be found.")
    return value


def _vehicle_payload(snapshot):
    return {**_plain(snapshot.vehicle), "accepted_connector_ids": sorted(set(snapshot.accepted_connector_ids))}


def _station_payload(snapshot, evaluation):
    names = {c.connector_type_id: c.name for c in snapshot.connector_types}
    return {
        **_plain(evaluation),
        "station": _plain(snapshot.station),
        "ports": [{**_plain(port), "connector_name": names.get(port.connector_type_id, "Unknown connector")} for port in snapshot.ports],
        "operating_periods": _plain(snapshot.operating_periods),
        "organizations": _plain(snapshot.organizations),
        "source": _plain(snapshot.metadata),
    }


class ApplicationService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], health_check: Callable[[], bool]):
        self._uow_factory = uow_factory
        self._health_check = health_check

    def health(self) -> bool:
        return self._health_check()

    def list_drivers(self) -> list[dict]:
        with self._uow_factory() as uow:
            return _plain(uow.drivers.list())

    def get_driver(self, driver_id: int) -> dict:
        with self._uow_factory() as uow:
            return _plain(_found(uow.drivers.get(_id(driver_id, "driver_id")), "driver"))

    def save_driver(self, data: dict, driver_id: int | None = None) -> dict:
        with self._uow_factory() as uow:
            if driver_id is not None:
                driver_id = _id(driver_id, "driver_id")
                _found(uow.drivers.get(driver_id), "driver")
            driver = Driver(driver_id, _text(data, "licence_number", 30, True), _text(data, "name", 100), _text(data, "carrier_name", 200))
            saved = uow.drivers.save(driver)
            uow.commit()
            return _plain(saved)

    def delete_driver(self, driver_id: int) -> None:
        with self._uow_factory() as uow:
            driver_id = _id(driver_id, "driver_id")
            _found(uow.drivers.get(driver_id), "driver")
            uow.drivers.delete(driver_id)
            uow.commit()

    def list_vehicles(self) -> list[dict]:
        with self._uow_factory() as uow:
            return [_vehicle_payload(vehicle) for vehicle in uow.vehicles.list()]

    def get_vehicle(self, vehicle_id: int) -> dict:
        with self._uow_factory() as uow:
            return _vehicle_payload(_found(uow.vehicles.get(_id(vehicle_id, "vehicle_id")), "vehicle"))

    def save_vehicle(self, data: dict, vehicle_id: int | None = None) -> dict:
        vehicle_class = _text(data, "vehicle_class", 30)
        if vehicle_class and vehicle_class not in {"CAR", "VAN", "MEDIUM_TRUCK", "HEAVY_TRUCK"}:
            raise InputError("Select a vehicle class.", {"vehicle_class": "Select a supported vehicle class."})
        accepted = data.get("accepted_connector_ids")
        if not isinstance(accepted, (list, tuple, set)) or not accepted:
            raise InputError("Select at least one accepted connector.", {"accepted_connector_ids": "Select at least one connector."})
        accepted_ids = sorted({_id(item, "accepted_connector_ids") for item in accepted})
        with self._uow_factory() as uow:
            if vehicle_id is not None:
                vehicle_id = _id(vehicle_id, "vehicle_id")
                _found(uow.vehicles.get(vehicle_id), "vehicle")
            known = {item.connector_type_id for item in uow.catalog.connectors()}
            if not set(accepted_ids).issubset(known):
                raise InputError("The connector is not registered.", {"accepted_connector_ids": "Select a connector from the list."})
            vehicle = Vehicle(vehicle_id, _text(data, "vin", 17, True), _text(data, "licence_plate", 15), _text(data, "make", 50), _text(data, "model", 50), vehicle_class, _number(data, "range_km", integer=True), _number(data, "max_charge_kw"))
            saved = uow.vehicles.save(vehicle, accepted_ids)
            uow.commit()
            return _vehicle_payload(saved)

    def delete_vehicle(self, vehicle_id: int) -> None:
        with self._uow_factory() as uow:
            vehicle_id = _id(vehicle_id, "vehicle_id")
            _found(uow.vehicles.get(vehicle_id), "vehicle")
            uow.vehicles.delete(vehicle_id)
            uow.commit()

    def list_memberships(self, driver_id: int | None = None) -> list[dict]:
        if driver_id is not None:
            driver_id = _id(driver_id, "driver_id")
        with self._uow_factory() as uow:
            return _plain(uow.memberships.list(driver_id))

    def get_membership(self, membership_id: int) -> dict:
        with self._uow_factory() as uow:
            return _plain(_found(uow.memberships.get(_id(membership_id, "membership_id")), "membership"))

    def save_membership(self, data: dict, membership_id: int | None = None) -> dict:
        driver_id, network_id = _id(data.get("driver_id"), "driver_id"), _id(data.get("network_id"), "network_id")
        start_date, end_date = _day(data, "start_date", True), _day(data, "end_date")
        membership = Membership(membership_id, driver_id, network_id, start_date, end_date)
        with self._uow_factory() as uow:
            if membership_id is not None:
                _found(uow.memberships.get(_id(membership_id, "membership_id")), "membership")
            _found(uow.drivers.get(driver_id), "driver")
            if network_id not in {network.organization_id for network in uow.catalog.networks()}:
                raise InputError("Select a charging network.", {"network_id": "The network is not registered."})
            saved = uow.memberships.save(membership)
            uow.commit()
            return _plain(saved)

    def delete_membership(self, membership_id: int) -> None:
        with self._uow_factory() as uow:
            membership_id = _id(membership_id, "membership_id")
            _found(uow.memberships.get(membership_id), "membership")
            uow.memberships.delete(membership_id)
            uow.commit()

    def catalog(self) -> dict:
        with self._uow_factory() as uow:
            return {"connectors": _plain(uow.catalog.connectors()), "networks": _plain(uow.catalog.networks())}

    def _selected(self, uow, driver_id, vehicle_id):
        driver = _found(uow.drivers.get(_id(driver_id, "driver_id")), "driver")
        vehicle = _found(uow.vehicles.get(_id(vehicle_id, "vehicle_id")), "vehicle")
        return driver, vehicle, uow.memberships.list(driver.driver_id)

    def search(self, driver_id: int, vehicle_id: int, arrival_at, bbox: dict, status: str = "ALL") -> dict:
        evaluation_at = datetime.now(timezone.utc)
        arrival = parse_arrival(arrival_at, evaluation_at)
        if status not in {"ALL", "AVAILABLE", "NEEDS_REVIEW", "UNAVAILABLE"}:
            raise InputError("Check the result status.", {"status": "This status is not supported."})
        try:
            west, south, east, north = [Decimal(str(bbox[key])) for key in ("west", "south", "east", "north")]
            if not all(v.is_finite() for v in (west, south, east, north)) or not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                raise ValueError
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise InputError("Check the search map bounds.", {"bbox": "Enter valid coordinates with west < east and south < north."}) from None
        counts = {"AVAILABLE": 0, "NEEDS_REVIEW": 0, "UNAVAILABLE": 0}
        results = []
        with self._uow_factory() as uow:
            driver, vehicle, memberships = self._selected(uow, driver_id, vehicle_id)
            for snapshot in uow.stations.list():
                station = snapshot.station
                if not (west <= station.longitude <= east and south <= station.latitude <= north):
                    continue
                result = evaluate_station(snapshot, vehicle, memberships, arrival, driver_id=driver.driver_id)
                payload = _station_payload(snapshot, result)
                counts[payload["overall_status"]] += 1
                if status == "ALL" or payload["overall_status"] == status:
                    results.append(payload)
        return {"driver_id": int(driver_id), "vehicle_id": int(vehicle_id), "arrival_at": arrival.isoformat(), "evaluation_at": evaluation_at.isoformat(), "results": results, "counts": counts}

    def detail(self, station_id: int, driver_id: int, vehicle_id: int, arrival_at) -> dict:
        evaluation_at = datetime.now(timezone.utc)
        arrival = parse_arrival(arrival_at, evaluation_at)
        with self._uow_factory() as uow:
            driver, vehicle, memberships = self._selected(uow, driver_id, vehicle_id)
            station = _found(uow.stations.get(_id(station_id, "station_id")), "station")
            result = evaluate_station(station, vehicle, memberships, arrival, driver_id=driver.driver_id)
            return {**_station_payload(station, result), "evaluation_at": evaluation_at.isoformat()}
