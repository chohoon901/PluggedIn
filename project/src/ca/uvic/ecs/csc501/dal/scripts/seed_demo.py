"""Idempotent ORM demo seed. Any conflicting existing row aborts all inserts."""
from datetime import date
from decimal import Decimal
import json
from sqlalchemy import select
from ca.uvic.ecs.csc501.cmn.contracts.errors import ConflictError
from ..database import Database
from ..unit_of_work import SqlAlchemyUnitOfWork
from ..models import *


def _demo_rows():
    rows = [
        OrganizationModel(organization_id=1, name='Demo Charging Company', website=None),
        OrganizationModel(organization_id=2, name='Demo Other Network', website=None),
        SiteOwnerModel(organization_id=1, business_type='Demo charging site'),
        OperatorModel(organization_id=1, support_phone='000-000-0000'),
        NetworkModel(organization_id=1, payment_method='Membership or guest'),
        NetworkModel(organization_id=2, payment_method='Membership'),
        ConnectorTypeModel(connector_type_id=1, name='CCS1', max_power_kw=None),
        ConnectorTypeModel(connector_type_id=2, name='CHAdeMO', max_power_kw=None),
        DriverModel(driver_id=1, licence_number='DEMO-LIC-001', name='Mina', carrier_name='Demo Delivery'),
        DriverModel(driver_id=2, licence_number='DEMO-LIC-002', name='Jin', carrier_name=None),
        VehicleModel(vehicle_id=1, vin='DEMO0000000000001', licence_plate='DEMO-01', make='Demo', model='Van', vehicle_class='VAN', range_km=250, max_charge_kw=Decimal('100.0')),
        VehicleAcceptsModel(vehicle_accepts_id=1, vehicle_id=1, connector_type_id=1),
        MembershipModel(membership_id=1, driver_id=1, network_id=1, start_date=date(2026,1,1), end_date=None),
        MembershipModel(membership_id=2, driver_id=2, network_id=2, start_date=date(2026,1,1), end_date=None),
    ]
    period_id = 0
    for identifier in range(1, 6):
        rows.append(StationModel(station_id=identifier, latitude=Decimal('48.45') + Decimal(identifier)/100,
                                 longitude=Decimal('-123.30') - Decimal(identifier)/100, name=f'Demo {chr(64+identifier)}',
                                 street=None, city='Victoria', province='BC', status='ACTIVE', access_restriction='public',
                                 accepts_guest_payment=identifier == 5, max_vehicle_class='VAN', has_truck_parking=False,
                                 owner_id=1, operator_id=1, network_id=1))
        rows.append(PortModel(port_id=identifier, station_id=identifier, number=1, connector_type_id=2 if identifier==3 else 1,
                              power_kw=Decimal('150.0'), current_type='DC', quantity=1))
        days = [] if identifier == 4 else ['Mon','Tue','Wed','Thu','Fri'] if identifier == 2 else ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        for day in days:
            period_id += 1
            rows.append(OperatingPeriodModel(operating_period_id=period_id, station_id=identifier, day=day,
                                             open_time='09:00:00' if identifier==2 else '00:00:00',
                                             close_time='17:00:00' if identifier==2 else '24:00:00'))
    return rows


def _demo_metadata():
    return {str(identifier): {'timezone':'America/Vancouver', 'hoursCompleteness':'UNKNOWN' if identifier==4 else 'COMPLETE',
                              'portsCompleteness':'COMPLETE', 'aggregateCompleteness':'INCOMPLETE' if identifier==4 else 'COMPLETE',
                              'sourceLabel':'Local project demo data', 'sourceUpdatedAt':None, 'unconfirmedFields':[]}
            for identifier in range(1,6)}


def seed_demo(database: Database | None = None) -> None:
    database = database or Database()
    path = database.settings.metadata_path
    if path.exists():
        try:
            existing_document = json.loads(path.read_text(encoding='utf-8'))
            if existing_document.get('schemaVersion') != 1 or not isinstance(existing_document.get('stations'), dict):
                raise ValueError('Unsupported metadata format')
        except (ValueError, TypeError, AttributeError, OSError) as error:
            raise ConflictError('Existing metadata cannot be read; existing file preserved') from error
    # Keep the original document for conflict checks and preservation. Validated
    # read defaults must never be persisted over an existing user's metadata.
    metadata = existing_document['stations'] if path.exists() else {}
    expected_metadata = _demo_metadata()
    for key, value in expected_metadata.items():
        if key in metadata and metadata[key] != value:
            raise ConflictError(f'Demo metadata conflict: station {key}; existing data preserved')
    merged = {**metadata, **expected_metadata}
    # Database relation writes are a single transaction. Metadata is staged in memory
    # for deferred validation and written only after that transaction succeeds.
    with SqlAlchemyUnitOfWork(database) as work:
        work.metadata_override = merged
        for row in _demo_rows():
            mapper = row.__mapper__
            primary = mapper.primary_key[0].key
            existing = work.session.get(type(row), getattr(row, primary))
            if existing is not None:
                for attribute in mapper.column_attrs:
                    if getattr(existing, attribute.key) != getattr(row, attribute.key):
                        raise ConflictError(f'Demo row conflict: {row.__tablename__} {getattr(row, primary)}; existing data preserved')
            else:
                work.session.add(row)
                # Flush in dependency order: ORM models intentionally contain no
                # ownership relationships, so insertion order is explicit here.
                work.session.flush()
        work.commit()
    if merged != metadata:
        path = database.settings.metadata_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps({'schemaVersion':1,'stations':merged}, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)


if __name__ == '__main__':
    seed_demo()
    print('Demo data verified or inserted; existing values preserved.')
