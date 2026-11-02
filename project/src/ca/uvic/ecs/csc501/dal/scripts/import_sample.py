"""Build a separate, source-traceable 20-station NLR/OCM snapshot (no OSM)."""
import argparse
import csv
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from ...cmn.connector_family import ConnectorFamily
from ..database import Database
from ..settings import Settings
from ..unit_of_work import SqlAlchemyUnitOfWork
from ..models import (OrganizationModel, NetworkModel, OperatorModel, StationModel,
                      ConnectorTypeModel, PortModel, OperatingPeriodModel, DriverModel,
                      VehicleModel, VehicleAcceptsModel, MembershipModel)
from .init_db import init_database
from .validate_db import validate_database


# 서로 다른 규격·운영시간·이용제한을 포함하는 Vancouver 인근 원본 ID입니다.
SAMPLE_IDS = ('404841', '439515', '422669', '434877', '329666', '388224',
              '357179', '435946', '404546', '84990', '437419', '436202',
              '262617', '428579', '421199', '421009', '84137', '208845', '249441', '84339')
DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def parse_hours(text):
    """Only fully understood schedules are complete; never guess business hours."""
    if text.lower().startswith('24 hours daily'):
        return [(day, '00:00:00', '24:00:00') for day in DAYS], 'COMPLETE'
    chunks = text.split('; ')
    pattern = r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun): (\d{1,2}:\d{2}[ap]m)-(\d{1,2}:\d{2}[ap]m)'
    matches = [re.fullmatch(pattern, chunk) for chunk in chunks]
    if len(matches) == 7 and all(matches) and {m[1] for m in matches} == set(DAYS):
        rows = [(m[1], datetime.strptime(m[2], '%I:%M%p').strftime('%H:%M:%S'),
                 datetime.strptime(m[3], '%I:%M%p').strftime('%H:%M:%S')) for m in matches]
        if all(start < end for _, start, end in rows):
            return rows, 'COMPLETE'
    daily = re.fullmatch(r'(\d{1,2})(am|pm)-(\d{1,2})(am|pm) daily', text, re.I)
    if daily:
        start = datetime.strptime(daily[1] + daily[2], '%I%p').strftime('%H:%M:%S')
        end = datetime.strptime(daily[3] + daily[4], '%I%p').strftime('%H:%M:%S')
        if start < end:
            return [(day, start, end) for day in DAYS], 'COMPLETE'
    return [], 'UNKNOWN'


def _access(row):
    text = row['Access Days Time'].lower()
    for token, value in (('fleet', 'fleet only'), ('employee', 'employees only'),
                         ('customer', 'customers only'), ('guest', 'guests only'),
                         ('card key', 'access key required')):
        if token in text:
            return value
    if row['Access Detail Code'] or row['Restricted Access'].upper() == 'TRUE':
        return row['Access Detail Code'] or 'restricted access'
    return row['Access Code'] or None


def build_sample(dal_root: Path, csv_path: Path, ocm_path: Path):
    """Refuse occupied destinations; keep all station source rows in a manifest."""
    if dal_root.exists() and any(dal_root.iterdir()):
        raise FileExistsError(f'Output directory is not empty: {dal_root}')
    with csv_path.open(encoding='cp1252', newline='') as handle:
        nlr = {row['ID']: row for row in csv.DictReader(handle)}
    ocm_rows = json.loads(ocm_path.read_text(encoding='utf-8-sig'))
    joined = {}
    for row in ocm_rows:
        reference = str(row.get('DataProvidersReference'))
        if row.get('DataProviderID') == 2 and reference in SAMPLE_IDS:
            if reference in joined:
                raise ValueError(f'Ambiguous OCM source reference: {reference}')
            joined[reference] = row
    pairs = [(nlr[identifier], joined[identifier]) for identifier in SAMPLE_IDS]
    for n, o in pairs:
        a = o['AddressInfo']
        if (n['State'] != 'BC' or n['Fuel Type Code'] != 'ELEC' or
                not 49.15 <= float(n['Latitude']) <= 49.35 or
                not -123.30 <= float(n['Longitude']) <= -122.85 or
                abs(float(n['Latitude']) - a['Latitude']) > .0005 or
                abs(float(n['Longitude']) - a['Longitude']) > .0007):
            raise ValueError(f'Source match requires review: {n["ID"]}')
    dal_root.mkdir(parents=True, exist_ok=True)
    (dal_root / 'config.properties').write_text(
        '[sqlite]\ndatabase_path=data/nlr_ocm_sample20.db\nmetadata_path=data/station_metadata.json\n', encoding='utf-8')
    db = Database(Settings(dal_root))
    metadata, manifest = {}, []
    init_database(db)
    try:
        with SqlAlchemyUnitOfWork(db) as work:
            organizations, connectors, networks = {}, {}, set()

            def organization(name, role, website=None, phone=None):
                if name not in organizations:
                    obj = OrganizationModel(name=name, website=website)
                    work.session.add(obj)
                    work.session.flush()
                    organizations[name] = (obj.organization_id, set())
                identifier, roles = organizations[name]
                if role not in roles:
                    work.session.add(NetworkModel(organization_id=identifier, payment_method=None) if role == 'network'
                                     else OperatorModel(organization_id=identifier, support_phone=phone))
                    work.session.flush()
                    roles.add(role)
                if role == 'network':
                    networks.add(identifier)
                return identifier

            def connector(name):
                if name not in connectors:
                    obj = ConnectorTypeModel(name=name, max_power_kw=None)
                    work.session.add(obj)
                    work.session.flush()
                    connectors[name] = obj.connector_type_id
                return connectors[name]

            for station_id, (n, o) in enumerate(pairs, 1):
                periods, hours_complete = parse_hours(n['Access Days Time'])
                network = None if n['EV Network'] in ('', 'Non-Networked') else organization(
                    n['EV Network'], 'network', n['EV Network Web'] or None)
                operator = o.get('OperatorInfo') or {}
                operator_id = None
                if operator.get('Title') and operator.get('ID') not in (1, 44):
                    operator_id = organization(operator['Title'], 'operator', operator.get('WebsiteURL'), operator.get('PhonePrimaryContact'))
                work.session.add(StationModel(station_id=station_id, latitude=Decimal(n['Latitude']),
                    longitude=Decimal(n['Longitude']), name=n['Station Name'], street=n['Street Address'] or None,
                    city=n['City'] or None, province=n['State'], status={'E': 'ACTIVE', 'T': 'TEMPORARILY_CLOSED', 'P': 'PLANNED'}.get(n['Status Code'], 'UNKNOWN'),
                    access_restriction=_access(n), accepts_guest_payment=False, max_vehicle_class=n['Maximum Vehicle Class'] or None,
                    has_truck_parking=False, owner_id=None, operator_id=operator_id, network_id=network))
                work.session.flush()
                nlr_types = n['EV Connector Types'].split()
                for name in nlr_types:
                    connector(name)  # Preserve both source vocabularies, with separate IDs.
                represented = set()
                for number, c in enumerate(o['Connections'], 1):
                    name = (c.get('ConnectionType') or {}).get('Title') or 'Unknown'
                    family = ConnectorFamily.from_name(name)
                    represented.add(family)
                    current = (c.get('CurrentType') or {}).get('Title', '')
                    current = 'DC' if current == 'DC' else 'AC' if current.startswith('AC') else None
                    work.session.add(PortModel(station_id=station_id, number=number, connector_type_id=connector(name),
                        power_kw=None, current_type=current, quantity=c.get('Quantity') or 1))
                number = len(o['Connections'])
                for name in nlr_types:
                    family = ConnectorFamily.from_name(name)
                    if family not in represented:
                        number += 1
                        work.session.add(PortModel(station_id=station_id, number=number, connector_type_id=connector(name),
                            power_kw=None, current_type=family.verified_current, quantity=1))
                for day, start, end in periods:
                    work.session.add(OperatingPeriodModel(station_id=station_id, day=day, open_time=start, close_time=end))
                unconfirmed = ['accepts_guest_payment', 'has_truck_parking', 'quantity', 'power_kw']
                metadata[str(station_id)] = {'timezone': 'America/Vancouver', 'hoursCompleteness': hours_complete,
                    'portsCompleteness': 'PARTIAL', 'aggregateCompleteness': 'INCOMPLETE',
                    'sourceLabel': f'NLR/AFDC {n["ID"]} + OCM {o["ID"]}; OCM power is estimated and not used',
                    'sourceUpdatedAt': n['Updated At'] or None, 'unconfirmedFields': unconfirmed}
                manifest.append({'station_id': station_id, 'nlr': n, 'ocm': o,
                    'decisions': {'owner': 'Unknown: NULL', 'operator': 'OCM OperatorInfo only; no inferred owner',
                        'power': 'NULL: linked OCM values are estimates, not verified equipment ratings',
                        'quantity': 'OCM summary count retained; physical port meaning unconfirmed',
                        'vehicle_class': 'NLR raw code retained; unsupported classifications stay UNKNOWN',
                        'ports': 'Partial source summaries, never asserted exhaustive',
                        'hours': hours_complete, 'payment': 'Unconfirmed, not inferred from free/card/app text'}})
            for identifier, name in ((1, 'Sample member (synthetic)'), (2, 'Sample visitor (synthetic)')):
                work.session.add(DriverModel(driver_id=identifier, licence_number=f'SAMPLE-LIC-{identifier}', name=name, carrier_name='Synthetic test profile'))
            for identifier, name in enumerate(('J1772COMBO', 'J1772', 'CHADEMO', 'TESLA'), 1):
                work.session.add(VehicleModel(vehicle_id=identifier, vin=f'SAMPLE{identifier:011d}', make='Sample', model=f'{name} test car (synthetic)', vehicle_class='CAR', max_charge_kw=Decimal('100')))
                work.session.flush()
                work.session.add(VehicleAcceptsModel(vehicle_id=identifier, connector_type_id=connector(name)))
            work.session.flush()
            for identifier in sorted(networks):
                work.session.add(MembershipModel(driver_id=1, network_id=identifier, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)))
            work.metadata_override = metadata
            work.commit()
        db.settings.metadata_path.write_text(json.dumps({'schemaVersion': 1, 'stations': metadata}, ensure_ascii=False, indent=2), encoding='utf-8')
        (dal_root / 'source_manifest.json').write_text(json.dumps({'schemaVersion': 1,
            'sources': [{'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in (csv_path, ocm_path)],
            'csvDecoding': 'cp1252; source bytes retained, existing mixed-encoding text not repaired',
            'stations': manifest}, ensure_ascii=False, indent=2), encoding='utf-8')
        issues = validate_database(db)
        if issues:
            raise ValueError('; '.join(issues))
    finally:
        db.engine.dispose()
    return db.settings.database_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--ocm', type=Path, required=True)
    args = parser.parse_args()
    print(build_sample(args.output_root, args.csv, args.ocm))
