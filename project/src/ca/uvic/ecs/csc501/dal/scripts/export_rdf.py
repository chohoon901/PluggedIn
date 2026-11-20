"""Export a read-only SQLite snapshot as RDF/XML instance data for Virtuoso."""

import argparse
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import re
import sqlite3
from xml.etree import ElementTree as ET

from ...cmn.enums.connector_family import ConnectorFamily
from ..metadata import read_metadata
from ..settings import Settings


PROJECT = 'https://github.com/chohoon901/PluggedIn/'
ONTOLOGY = PROJECT + 'ontology/'
MIGRATION = PROJECT + 'migration/'
RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
XSD = 'http://www.w3.org/2001/XMLSchema#'

# Each entry maps a table to its RDF class, primary key and non-key attributes.
TABLES = {
    'organization': ('Organization', 'organization_id', {'name': 'orgName', 'website': 'website'}),
    'site_owner': ('SiteOwner', 'organization_id', {'business_type': 'businessType'}),
    'operator': ('Operator', 'organization_id', {'support_phone': 'supportPhone'}),
    'network': ('Network', 'organization_id', {'payment_method': 'paymentMethod'}),
    'station': ('Station', 'station_id', {
        'latitude': 'latitude', 'longitude': 'longitude', 'name': 'stationName',
        'street': 'street', 'city': 'city', 'province': 'province', 'status': 'status',
        'access_restriction': 'accessRestriction', 'accepts_guest_payment': 'acceptsGuestPayment',
        'max_vehicle_class': 'maxVehicleClass', 'has_truck_parking': 'hasTruckParking',
    }),
    'connector_type': ('ConnectorType', 'connector_type_id', {
        'name': 'connectorName', 'max_power_kw': 'connectorMaxPowerKw',
    }),
    'port': ('Port', 'port_id', {
        'number': 'portNumber', 'power_kw': 'powerKw', 'current_type': 'currentType', 'quantity': 'quantity',
    }),
    'operating_period': ('OperatingPeriod', 'operating_period_id', {
        'day': 'day', 'open_time': 'openTime', 'close_time': 'closeTime',
    }),
    'adapter': ('Adapter', 'adapter_id', {
        'model': 'adapterModel', 'manufacturer': 'manufacturer', 'max_power_kw': 'adapterMaxPowerKw',
    }),
    'vehicle': ('Vehicle', 'vehicle_id', {
        'vin': 'vin', 'licence_plate': 'licencePlate', 'make': 'make', 'model': 'vehicleModel',
        'class': 'vehicleClass', 'range_km': 'rangeKm', 'max_charge_kw': 'vehicleMaxChargeKw',
    }),
    'vehicle_accepts': ('VehicleAcceptance', 'vehicle_accepts_id', {}),
    'driver': ('Driver', 'driver_id', {'licence_number': 'licenceNumber', 'name': 'driverName', 'carrier_name': 'carrierName'}),
    'membership': ('Membership', 'membership_id', {'start_date': 'startDate', 'end_date': 'endDate'}),
}

# Column -> (predicate, referenced table). The referenced resource is the subject
# for hasPort, hasOperatingPeriod and hasMembership in the approved vocabulary.
RELATIONS = {
    'station': {'owner_id': ('ownedBy', 'organization'), 'operator_id': ('operatedBy', 'organization'),
                'network_id': ('partOfNetwork', 'organization')},
    'port': {'station_id': ('hasPort', 'station'), 'connector_type_id': ('hasConnectorType', 'connector_type')},
    'operating_period': {'station_id': ('hasOperatingPeriod', 'station')},
    'adapter': {'from_connector_type_id': ('fromConnector', 'connector_type'),
                'to_connector_type_id': ('toConnector', 'connector_type')},
    'vehicle_accepts': {'vehicle_id': ('acceptingVehicle', 'vehicle'),
                        'connector_type_id': ('acceptedConnector', 'connector_type')},
    'membership': {'driver_id': ('hasMembership', 'driver'), 'network_id': ('belongsToNetwork', 'organization')},
}
REVERSE = {'hasPort', 'hasOperatingPeriod', 'hasMembership'}
ORG_ROLES = {'site_owner', 'operator', 'network'}
LITERAL_TYPES = dict.fromkeys(('latitude', 'longitude', 'powerKw', 'connectorMaxPowerKw',
                              'adapterMaxPowerKw', 'vehicleMaxChargeKw', 'rangeKm'), 'decimal')
LITERAL_TYPES.update(portNumber='integer', quantity='integer', acceptsGuestPayment='boolean', hasTruckParking='boolean')
UNCERTAIN_COLUMNS = {'accepts_guest_payment', 'has_truck_parking', 'quantity', 'power_kw'}
METADATA_FIELDS = ('timezone', 'hoursCompleteness', 'portsCompleteness', 'aggregateCompleteness',
                   'sourceLabel', 'sourceUpdatedAt')


def _name(namespace, local_name):
    return f'{{{namespace}}}{local_name}'


def _link(node, namespace, predicate, target):
    ET.SubElement(node, _name(namespace, predicate), {_name(RDF, 'resource'): target})


def _literal(node, namespace, predicate, value, datatype='string'):
    if datatype == 'decimal':
        value = format(Decimal(str(value)), 'f')
    elif datatype == 'boolean':
        value = 'true' if value else 'false'
    ET.SubElement(node, _name(namespace, predicate), {_name(RDF, 'datatype'): XSD + datatype}).text = str(value)


def export_rdf(settings: Settings, output_path: Path, *, dataset: str) -> dict[str, int]:
    """Write a new RDF/XML file and return source counts for all 13 tables.

    IDs live in dataset-qualified resource IRIs. Shared organization IDs keep
    role types on one resource. VehicleAcceptance retains the join-row ID alongside
    the ontology's direct vehicleAccepts edge. Migration properties store metadata
    and DB defaults that the source marks unconfirmed, plus known connector families.
    """
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', dataset):
        raise ValueError('Dataset must use letters, digits, hyphens or underscores.')
    ET.register_namespace('rdf', RDF)
    ET.register_namespace('plug', ONTOLOGY)
    ET.register_namespace('migration', MIGRATION)
    document = ET.Element(_name(RDF, 'RDF'))
    nodes = {}
    counts = {}
    metadata = read_metadata(settings)

    def resource(table, identifier):
        resource_class = 'Organization' if table in ORG_ROLES else TABLES[table][0]
        return f'{PROJECT}data/{dataset}/{resource_class}/{identifier}'

    def node_for(iri):
        if iri not in nodes:
            nodes[iri] = ET.SubElement(document, _name(RDF, 'Description'), {_name(RDF, 'about'): iri})
        return nodes[iri]

    with closing(sqlite3.connect(settings.database_path.as_uri() + '?mode=ro', uri=True,
                                 timeout=settings.busy_timeout_ms / 1000)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute('BEGIN')
        if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise ValueError('The source database has broken foreign key references.')

        for table, (resource_class, key, fields) in TABLES.items():
            relations = RELATIONS.get(table, {})
            rows = connection.execute(f'SELECT * FROM "{table}" ORDER BY "{key}"')
            expected = {key, *fields, *relations}
            if {column[0] for column in rows.description} != expected:
                raise ValueError(f'Source columns do not match the RDF mapping for {table}.')
            counts[table] = 0
            class_namespace = MIGRATION if table == 'vehicle_accepts' else ONTOLOGY

            for row in rows:
                counts[table] += 1
                iri = resource(table, row[key])
                node = node_for(iri)
                _link(node, RDF, 'type', class_namespace + resource_class)
                station_id = row['station_id'] if table in ('station', 'port') else None
                evidence = metadata.get(str(station_id), {})
                unconfirmed = evidence.get('unconfirmedFields', ()) if evidence else UNCERTAIN_COLUMNS
                uncertain = {field.rsplit('.', 1)[-1] for field in unconfirmed}

                for column, predicate in fields.items():
                    if row[column] is None:
                        continue
                    datatype = LITERAL_TYPES.get(predicate, 'string')
                    if column in UNCERTAIN_COLUMNS and column in uncertain:
                        recorded = 'recorded' + predicate[0].upper() + predicate[1:]
                        _literal(node, MIGRATION, recorded, row[column], datatype)
                    else:
                        _literal(node, ONTOLOGY, predicate, row[column], datatype)

                for column, (predicate, target_table) in relations.items():
                    if row[column] is None:
                        continue
                    target = resource(target_table, row[column])
                    if predicate in REVERSE:
                        _link(node_for(target), ONTOLOGY, predicate, iri)
                    else:
                        _link(node, class_namespace, predicate, target)

                if table == 'vehicle_accepts':
                    vehicle = node_for(resource('vehicle', row['vehicle_id']))
                    _link(vehicle, ONTOLOGY, 'vehicleAccepts', resource('connector_type', row['connector_type_id']))
                elif table == 'connector_type':
                    family = ConnectorFamily.from_name(row['name'])
                    if family is not ConnectorFamily.UNKNOWN:
                        _literal(node, MIGRATION, 'connectorFamily', family.value)
                elif table == 'station':
                    for field in METADATA_FIELDS:
                        if evidence.get(field) is not None:
                            _literal(node, MIGRATION, field, evidence[field])
                    for field in sorted(unconfirmed):
                        _literal(node, MIGRATION, 'unconfirmedField', field)

    ET.indent(document)
    rdf_bytes = ET.tostring(document, encoding='utf-8', xml_declaration=True)
    ET.fromstring(rdf_bytes)
    with output_path.open('xb') as output:
        output.write(rdf_bytes)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, help='Stable dataset identifier used in resource IRIs')
    parser.add_argument('--output', required=True, type=Path, help='New RDF/XML file to create')
    parser.add_argument('--dal-root', type=Path, help='Directory containing the source config.properties')
    args = parser.parse_args()
    try:
        counts = export_rdf(Settings(args.dal_root), args.output, dataset=args.dataset)
    except (OSError, ValueError, sqlite3.Error, ET.ParseError) as error:
        parser.exit(1, f'{error}\n')
    print(f'Wrote {args.output} from {sum(counts.values())} SQLite rows.')
    print(', '.join(f'{table}={count}' for table, count in counts.items()))


if __name__ == '__main__':
    main()
