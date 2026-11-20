"""Map one Virtuoso graph snapshot to the application's persistence contracts."""

from collections import defaultdict
from dataclasses import asdict

from ...cmn.contracts.errors import ConflictError, InputError, NotFoundError, NotReadyError
from ...cmn.contracts.models import StationSnapshot, VehicleSnapshot
from ...cmn.domain.connector_type import ConnectorType
from ...cmn.domain.driver import Driver
from ...cmn.domain.membership import Membership
from ...cmn.domain.operating_period import OperatingPeriod
from ...cmn.domain.organization import Organization
from ...cmn.domain.port import Port
from ...cmn.domain.station import Station
from ...cmn.domain.vehicle import Vehicle
from .rdf import MIGRATION, Dataset


_EDITABLE = ('driver', 'vehicle', 'vehicle_accepts', 'membership')
_CONSTRAINT_ERROR = 'Check for duplicate values or data relationship and range constraints.'


class _Entities:
    def __init__(self, rows, entity_type):
        self.rows = rows
        self._entity_type = entity_type

    def get(self, identifier):
        row = self.rows.get(identifier)
        return self._entity_type(**row) if row is not None else None

    def list(self):
        return [self.get(identifier) for identifier in sorted(self.rows)]


class _EditableEntities(_Entities):
    def __init__(self, rows, entity_type, key):
        super().__init__(rows, entity_type)
        self._key = key

    def save(self, entity):
        row = asdict(entity)
        identifier = row[self._key]
        if identifier is None:
            identifier = max(self.rows, default=0) + 1
        elif identifier not in self.rows:
            raise NotFoundError('The registered item could not be found.')
        row[self._key] = identifier
        self.rows[identifier] = row
        return self.get(identifier)

    def delete(self, identifier):
        self.rows.pop(identifier, None)


class _Drivers(_EditableEntities):
    def __init__(self, rows, memberships):
        super().__init__(rows, Driver, 'driver_id')
        self._memberships = memberships

    def delete(self, identifier):
        super().delete(identifier)
        for membership in self._memberships.list(identifier):
            self._memberships.delete(membership.membership_id)


class _Memberships(_EditableEntities):
    def __init__(self, rows):
        super().__init__(rows, Membership, 'membership_id')

    def list(self, driver_id=None):
        return [self.get(identifier) for identifier, row in sorted(self.rows.items())
                if driver_id is None or row['driver_id'] == driver_id]


class _Vehicles:
    def __init__(self, rows, acceptances, connectors):
        self._rows = rows
        self._acceptances = acceptances
        self._connectors = connectors

    def get(self, identifier):
        row = self._rows.get(identifier)
        if row is None:
            return None
        values = dict(row)
        values['vehicle_class'] = values.pop('class')
        connector_ids = tuple(sorted(link['connector_type_id'] for link in self._acceptances.values()
                                     if link['vehicle_id'] == identifier))
        return VehicleSnapshot(Vehicle(**values), connector_ids,
                               tuple(self._connectors[key].name for key in connector_ids))

    def list(self):
        return [self.get(identifier) for identifier in sorted(self._rows)]

    def save(self, vehicle, accepted_connector_ids):
        desired = set(accepted_connector_ids)
        if not desired:
            raise InputError('Select at least one accepted connector.')
        if not desired <= self._connectors.keys():
            raise ConflictError(_CONSTRAINT_ERROR)
        identifier = vehicle.vehicle_id
        if identifier is None:
            identifier = max(self._rows, default=0) + 1
        elif identifier not in self._rows:
            raise NotFoundError('The registered item could not be found.')
        row = asdict(vehicle)
        row['vehicle_id'] = identifier
        row['class'] = row.pop('vehicle_class')
        self._rows[identifier] = row

        existing = {link['connector_type_id']: key for key, link in self._acceptances.items()
                    if link['vehicle_id'] == identifier}
        for connector_id in existing.keys() - desired:
            del self._acceptances[existing[connector_id]]
        next_id = max(self._acceptances, default=0) + 1
        for key, connector_id in enumerate(sorted(desired - existing.keys()), start=next_id):
            self._acceptances[key] = {
                'vehicle_accepts_id': key, 'vehicle_id': identifier, 'connector_type_id': connector_id,
            }
        return self.get(identifier)

    def delete(self, identifier):
        self._rows.pop(identifier, None)
        for key, link in list(self._acceptances.items()):
            if link['vehicle_id'] == identifier:
                del self._acceptances[key]


class _Catalog:
    def __init__(self, connectors, networks):
        self._connectors = connectors
        self._networks = networks

    def connectors(self):
        return [self._connectors[key] for key in sorted(self._connectors)]

    def networks(self):
        return [self._networks[key] for key in sorted(self._networks)]


class _Stations:
    def __init__(self, dataset, connectors, organizations):
        self._dataset = dataset
        self._facilities = dataset.records('station')
        self._connectors = connectors
        self._organizations = organizations
        self._ports = defaultdict(list)
        self._periods = defaultdict(list)
        for key, row in sorted(dataset.records('port').items()):
            if any(predicate == MIGRATION + 'recordedPowerKw'
                   for _, predicate, _ in dataset.record_triples('port', key)):
                row = {**row, 'power_kw': None}
            self._ports[row['station_id']].append(Port(**row))
        for _, row in sorted(dataset.records('operating_period').items()):
            self._periods[row['station_id']].append(OperatingPeriod(**row))

    def get(self, identifier):
        row = self._facilities.get(identifier)
        if row is None:
            return None
        station = Station(**row)
        ports = tuple(self._ports.get(identifier, ()))
        connector_ids = sorted({port.connector_type_id for port in ports})
        organization_ids = sorted({station.owner_id, station.operator_id, station.network_id} - {None})
        return StationSnapshot(
            station, ports, tuple(self._periods.get(identifier, ())),
            tuple(self._connectors[key] for key in connector_ids),
            tuple(self._organizations[key] for key in organization_ids),
            self._dataset.station_evidence(identifier),
        )

    def list(self):
        return [self.get(identifier) for identifier in sorted(self._facilities)]


def _require_unique(rows, *fields):
    keys = {tuple(row[field] for field in fields) for row in rows.values()}
    if len(keys) != len(rows):
        raise ConflictError(_CONSTRAINT_ERROR)


class VirtuosoUnitOfWork:
    def __init__(self, store):
        self._store = store

    def __enter__(self):
        self._state = self._store.load()
        try:
            self._dataset = Dataset(self._store.dataset, self._state.triples)
            self._original = {table: self._dataset.records(table) for table in _EDITABLE}
            self._rows = {table: rows.copy() for table, rows in self._original.items()}
            organization_rows = self._dataset.records('organization')
            organizations = {key: Organization(**row) for key, row in organization_rows.items()}
            connectors = {key: ConnectorType(**row) for key, row in self._dataset.records('connector_type').items()}
            networks = {key: organizations[key] for key in self._dataset.records('network')}
            self.organizations = _Entities(organization_rows, Organization)
            self.memberships = _Memberships(self._rows['membership'])
            self.drivers = _Drivers(self._rows['driver'], self.memberships)
            self.vehicles = _Vehicles(self._rows['vehicle'], self._rows['vehicle_accepts'], connectors)
            self.catalog = _Catalog(connectors, networks)
            self.stations = _Stations(self._dataset, connectors, organizations)
        except (ValueError, KeyError) as exc:
            raise NotReadyError('The Virtuoso dataset is incomplete or invalid.') from exc
        return self

    def _check_profiles(self):
        drivers, vehicles = self._rows['driver'], self._rows['vehicle']
        memberships, acceptances = self._rows['membership'], self._rows['vehicle_accepts']
        _require_unique(drivers, 'licence_number')
        _require_unique(vehicles, 'vin')
        _require_unique(memberships, 'driver_id', 'network_id', 'start_date')
        _require_unique(acceptances, 'vehicle_id', 'connector_type_id')
        networks = {network.organization_id for network in self.catalog.networks()}
        if any(row['driver_id'] not in drivers or row['network_id'] not in networks
               for row in memberships.values()):
            raise ConflictError(_CONSTRAINT_ERROR)
        connectors = {connector.connector_type_id for connector in self.catalog.connectors()}
        if ({row['vehicle_id'] for row in acceptances.values()} != vehicles.keys()
                or any(row['connector_type_id'] not in connectors for row in acceptances.values())):
            raise ConflictError(_CONSTRAINT_ERROR)

    def commit(self):
        self._check_profiles()
        removed, added = set(), set()
        for table, previous in self._original.items():
            current = self._rows[table]
            for key in previous.keys() | current.keys():
                if previous.get(key) == current.get(key):
                    continue
                if key in previous:
                    removed.update(self._dataset.record_triples(table, key))
                if key in current:
                    added.update(self._dataset.encode(table, current[key]))
        if removed or added:
            self._state = self._store.commit(self._state, removed, added)
            self._dataset = Dataset(self._store.dataset, self._state.triples)
            self._original = {table: rows.copy() for table, rows in self._rows.items()}

    def rollback(self):
        for table, rows in self._rows.items():
            rows.clear()
            rows.update(self._original[table])

    def __exit__(self, exc_type, exc_value, traceback):
        self.rollback()
        return False
