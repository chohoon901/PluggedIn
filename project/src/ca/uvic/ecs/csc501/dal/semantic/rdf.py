"""Convert between PluggedIn rows and the approved Virtuoso RDF vocabulary."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re

from ...cmn.contracts.models import StationMetadata
from ...cmn.domain.value_objects.daily_time import DailyTime
from ...cmn.enums.connector_family import ConnectorFamily
from ..metadata import normalize_stations


PROJECT = 'https://github.com/chohoon901/PluggedIn/'
ONTOLOGY = PROJECT + 'ontology/'
MIGRATION = PROJECT + 'migration/'
RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
XSD = 'http://www.w3.org/2001/XMLSchema#'
RDF_TYPE = RDF + 'type'

# Table -> (RDF class, primary key, column-to-property mapping).
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
    'driver': ('Driver', 'driver_id', {
        'licence_number': 'licenceNumber', 'name': 'driverName', 'carrier_name': 'carrierName',
    }),
    'membership': ('Membership', 'membership_id', {'start_date': 'startDate', 'end_date': 'endDate'}),
}

# Foreign-key column -> (property, referenced table). Inverse edges name the
# referenced record as their subject. Organization roles share one resource.
RELATIONS = {
    'station': {'owner_id': ('ownedBy', 'site_owner'), 'operator_id': ('operatedBy', 'operator'),
                'network_id': ('partOfNetwork', 'network')},
    'port': {'station_id': ('hasPort', 'station'), 'connector_type_id': ('hasConnectorType', 'connector_type')},
    'operating_period': {'station_id': ('hasOperatingPeriod', 'station')},
    'adapter': {'from_connector_type_id': ('fromConnector', 'connector_type'),
                'to_connector_type_id': ('toConnector', 'connector_type')},
    'vehicle_accepts': {'vehicle_id': ('acceptingVehicle', 'vehicle'),
                        'connector_type_id': ('acceptedConnector', 'connector_type')},
    'membership': {'driver_id': ('hasMembership', 'driver'), 'network_id': ('belongsToNetwork', 'network')},
}
_INVERSE = {'hasPort', 'hasOperatingPeriod', 'hasMembership'}
_ORGANIZATION_ROLES = {'site_owner', 'operator', 'network'}
_REQUIRED_FIELDS = {
    'organization': {'name'},
    'station': {'latitude', 'longitude', 'accepts_guest_payment', 'has_truck_parking'},
    'connector_type': {'name'},
    'port': {'station_id', 'number', 'connector_type_id', 'quantity'},
    'operating_period': {'station_id', 'day', 'open_time', 'close_time'},
    'adapter': {'model', 'from_connector_type_id', 'to_connector_type_id'},
    'vehicle': {'vin'},
    'vehicle_accepts': {'vehicle_id', 'connector_type_id'},
    'driver': {'licence_number'},
    'membership': {'driver_id', 'network_id', 'start_date'},
}
_LITERAL_TYPES = dict.fromkeys(('latitude', 'longitude', 'power_kw', 'max_power_kw', 'max_charge_kw', 'range_km'), 'decimal')
_LITERAL_TYPES.update(number='integer', quantity='integer', accepts_guest_payment='boolean', has_truck_parking='boolean')
_RECORDED_FIELDS = {'station': {'accepts_guest_payment', 'has_truck_parking'}, 'port': {'quantity', 'power_kw'}}
_FALLBACK_FIELDS = _RECORDED_FIELDS['station'] | _RECORDED_FIELDS['port']
_METADATA_FIELDS = ('timezone', 'hoursCompleteness', 'portsCompleteness', 'aggregateCompleteness',
                    'sourceLabel', 'sourceUpdatedAt')
_ABSOLUTE_IRI = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:')
_IRI_FORBIDDEN = re.compile(r'[\x00-\x20\x7f<>"{}|^`\\\ud800-\udfff]|%(?![0-9A-Fa-f]{2})')
_SURROGATE = re.compile(r'[\ud800-\udfff]')
_LANGUAGE_TAG = re.compile(r'[A-Za-z]+(?:-[A-Za-z0-9]+)*')
_DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)')
_INTEGER = re.compile(r'[+-]?[0-9]+')
_INTEGER_TYPES = {XSD + name for name in ('integer', 'long', 'int', 'short', 'byte', 'positiveInteger',
                                         'nonNegativeInteger', 'nonPositiveInteger', 'negativeInteger',
                                         'unsignedLong', 'unsignedInt', 'unsignedShort', 'unsignedByte')}
_ROW_ID = re.compile(r'0|-?[1-9][0-9]*')


def iri_ref(value: str) -> str:
    if not isinstance(value, str) or not _ABSOLUTE_IRI.match(value) or _IRI_FORBIDDEN.search(value):
        raise ValueError('Expected an absolute RDF IRI.')
    return f'<{value}>'


@dataclass(frozen=True, slots=True)
class Term:
    value: str
    kind: str = 'literal'
    datatype: str | None = None
    language: str | None = None

    def __post_init__(self):
        if not isinstance(self.value, str) or _SURROGATE.search(self.value):
            raise ValueError('Expected an RDF term with a Unicode string value.')
        if self.kind == 'uri' and self.datatype is None and self.language is None:
            iri_ref(self.value)
            return
        if self.kind != 'literal' or (self.datatype is not None and self.language is not None):
            raise ValueError('Invalid RDF term kind or literal attributes.')
        if self.datatype is not None:
            iri_ref(self.datatype)
        if self.language is not None and (
            not isinstance(self.language, str) or not _LANGUAGE_TAG.fullmatch(self.language)
        ):
            raise ValueError('Invalid RDF language tag.')

    @classmethod
    def from_binding(cls, binding: Mapping[str, object]) -> 'Term':
        if not isinstance(binding, Mapping):
            raise ValueError('Expected a SPARQL result binding.')
        kind = binding.get('type')
        datatype = binding.get('datatype')
        language = binding.get('xml:lang')
        if ('datatype' in binding and not isinstance(datatype, str)
                or 'xml:lang' in binding and not isinstance(language, str)
                or kind == 'typed-literal' and datatype is None):
            raise ValueError('Invalid SPARQL literal attributes.')
        return cls(binding.get('value'), 'literal' if kind == 'typed-literal' else kind, datatype, language)

    def sparql(self) -> str:
        if self.kind == 'uri':
            return iri_ref(self.value)
        literal = json.dumps(self.value, ensure_ascii=False)
        if self.datatype is not None:
            return f'{literal}^^{iri_ref(self.datatype)}'
        if self.language is not None:
            return f'{literal}@{self.language}'
        return literal


type Triple = tuple[str, str, Term]


def sparql_triples(triples: Iterable[Triple]) -> str:
    return '\n'.join(sorted(
        f'{iri_ref(subject)} {iri_ref(predicate)} {term.sparql()} .'
        for subject, predicate, term in triples
    ))


def _namespace(table: str) -> str:
    return MIGRATION if table == 'vehicle_accepts' else ONTOLOGY


def _class_term(table: str) -> Term:
    return Term(_namespace(table) + TABLES[table][0], 'uri')


def _recorded_predicate(predicate: str) -> str:
    return MIGRATION + 'recorded' + predicate[0].upper() + predicate[1:]


def _literal(value, datatype: str = 'string') -> Term:
    if datatype == 'decimal':
        try:
            number = Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError('Expected a finite decimal value in the source row.') from error
        if not number.is_finite():
            raise ValueError('Expected a finite decimal value in the source row.')
        value = format(number, 'f')
    elif datatype == 'boolean':
        value = 'true' if value else 'false'
    return Term(str(value), datatype=XSD + datatype)


def _text(term: Term) -> str:
    if term.kind != 'literal' or term.language is not None or term.datatype not in (None, XSD + 'string'):
        raise ValueError('Expected an RDF string literal.')
    return term.value


def _decode_literal(column: str, term: Term):
    datatype = _LITERAL_TYPES.get(column, 'string')
    if datatype == 'string':
        value = _text(term)
        if column in ('open_time', 'close_time'):
            return DailyTime.parse(value)
        if column in ('start_date', 'end_date'):
            return date.fromisoformat(value)
        return value

    if term.kind == 'literal' and term.language is None:
        value = term.value.strip(' \t\r\n')
        if datatype == 'boolean' and term.datatype == XSD + 'boolean':
            if value in ('true', '1'):
                return True
            if value in ('false', '0'):
                return False
        elif datatype == 'integer' and term.datatype in _INTEGER_TYPES and _INTEGER.fullmatch(value):
            return int(value)
        elif datatype == 'decimal' and (
            term.datatype == XSD + 'decimal' and _DECIMAL.fullmatch(value)
            or term.datatype in _INTEGER_TYPES and _INTEGER.fullmatch(value)
        ):
            decimal_value = Decimal(value)
            if column != 'range_km':
                return decimal_value
            if decimal_value == decimal_value.to_integral_value():
                return int(decimal_value)
    raise ValueError(f'Invalid RDF literal for {column}.')


def _one(values, table: str, column: str):
    if len(values) == 1:
        return next(iter(values))
    if not values and column not in _REQUIRED_FIELDS.get(table, ()):
        return None
    raise ValueError(f'Expected one RDF value for {table}.{column}.')


class Dataset:
    def __init__(self, name: str, triples: Iterable[Triple] = ()):
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', name):
            raise ValueError('Dataset must use letters, digits, hyphens or underscores.')
        self._base = f'{PROJECT}data/{name}/'
        self._objects = defaultdict(set)
        self._subjects = defaultdict(set)
        for subject, predicate, term in triples:
            self._objects[subject, predicate].add(term)
            self._subjects[predicate, term].add(subject)

    def _resource_prefix(self, table: str) -> str:
        resource_class = 'Organization' if table in _ORGANIZATION_ROLES else TABLES[table][0]
        return f'{self._base}{resource_class}/'

    def resource(self, table: str, identifier: int) -> str:
        if type(identifier) is not int:
            raise ValueError(f'Expected an integer identifier for {table}.')
        return self._resource_prefix(table) + str(identifier)

    def _identifier(self, table: str, subject: str) -> int:
        identifier = subject.removeprefix(self._resource_prefix(table))
        if not _ROW_ID.fullmatch(identifier):
            raise ValueError(f'Invalid RDF resource identifier for {table}.')
        return int(identifier)

    def _vehicle_accepts(self, row: Mapping) -> Triple:
        return (self.resource('vehicle', row['vehicle_id']), ONTOLOGY + 'vehicleAccepts',
                Term(self.resource('connector_type', row['connector_type_id']), 'uri'))

    def _values(self, subject: str, predicate: str):
        return self._objects.get((subject, predicate), ())

    def encode(self, table: str, row: Mapping, *, evidence: Mapping | None = None) -> set[Triple]:
        """Encode a stored row using the original column names and RDF datatypes."""
        _, key, fields = TABLES[table]
        subject = self.resource(table, row[key])
        triples = {(subject, RDF_TYPE, _class_term(table))}
        evidence = evidence or {}
        unconfirmed = evidence.get('unconfirmedFields', ()) if evidence else _FALLBACK_FIELDS
        uncertain_columns = {field.rsplit('.', 1)[-1] for field in unconfirmed}

        for column, predicate in fields.items():
            value = row.get(column)
            if value is None:
                _one((), table, column)
                continue
            if column in _RECORDED_FIELDS.get(table, ()) and column in uncertain_columns:
                property_iri = _recorded_predicate(predicate)
            else:
                property_iri = ONTOLOGY + predicate
            triples.add((subject, property_iri, _literal(value, _LITERAL_TYPES.get(column, 'string'))))

        for column, (predicate, target_table) in RELATIONS.get(table, {}).items():
            value = row.get(column)
            if value is None:
                _one((), table, column)
                continue
            target = self.resource(target_table, value)
            if predicate in _INVERSE:
                triples.add((target, ONTOLOGY + predicate, Term(subject, 'uri')))
            else:
                triples.add((subject, _namespace(table) + predicate, Term(target, 'uri')))

        if table == 'vehicle_accepts':
            triples.add(self._vehicle_accepts(row))
        elif table == 'connector_type':
            family = ConnectorFamily.from_name(row['name'])
            if family is not ConnectorFamily.UNKNOWN:
                triples.add((subject, MIGRATION + 'connectorFamily', _literal(family.value)))
        elif table == 'station':
            triples.update((subject, MIGRATION + field, _literal(evidence[field]))
                           for field in _METADATA_FIELDS if evidence.get(field) is not None)
            triples.update((subject, MIGRATION + 'unconfirmedField', _literal(field)) for field in unconfirmed)
        return triples

    def _record(self, table: str, identifier: int, subject: str) -> tuple[dict, set[Triple]]:
        _, key, fields = TABLES[table]
        row = {key: identifier}
        triples = {(subject, RDF_TYPE, _class_term(table))}
        for column, predicate in fields.items():
            predicates = [ONTOLOGY + predicate]
            if column in _RECORDED_FIELDS.get(table, ()):
                predicates.append(_recorded_predicate(predicate))
            values = [(property_iri, term) for property_iri in predicates
                      for term in self._values(subject, property_iri)]
            match = _one(values, table, column)
            row[column] = None
            if match is not None:
                property_iri, term = match
                row[column] = _decode_literal(column, term)
                triples.add((subject, property_iri, term))

        for column, (predicate, target_table) in RELATIONS.get(table, {}).items():
            property_iri = _namespace(table) + predicate
            row[column] = None
            if predicate in _INVERSE:
                term = Term(subject, 'uri')
                sources = self._subjects.get((property_iri, term), ())
                source = _one([source for source in sources if source.startswith(self._base)], table, column)
                if source is not None:
                    row[column] = self._identifier(target_table, source)
                    triples.add((source, property_iri, term))
            else:
                term = _one(self._values(subject, property_iri), table, column)
                if term is not None:
                    if term.kind != 'uri':
                        raise ValueError(f'Expected an RDF resource for {table}.{column}.')
                    row[column] = self._identifier(target_table, term.value)
                    triples.add((subject, property_iri, term))

        if table == 'vehicle_accepts':
            vehicle, predicate, connector = self._vehicle_accepts(row)
            if connector in self._values(vehicle, predicate):
                triples.add((vehicle, predicate, connector))
        return row, triples

    def records(self, table: str) -> dict[int, dict]:
        """Return mapped columns for typed records in this dataset, ordered by ID."""
        subjects = self._subjects.get((RDF_TYPE, _class_term(table)), ())
        records = sorted((self._identifier(table, subject), subject)
                         for subject in subjects if subject.startswith(self._base))
        return {identifier: self._record(table, identifier, subject)[0] for identifier, subject in records}

    def record_triples(self, table: str, identifier: int) -> set[Triple]:
        """Return the actual schema triples owned by one stored record for updates."""
        subject = self.resource(table, identifier)
        if _class_term(table) not in self._values(subject, RDF_TYPE):
            return set()
        return self._record(table, identifier, subject)[1]

    def station_evidence(self, station_id: int) -> StationMetadata:
        subject = self.resource('station', station_id)
        evidence = {}
        for field in _METADATA_FIELDS:
            term = _one(self._values(subject, MIGRATION + field), 'station', field)
            if term is not None:
                evidence[field] = _text(term)

        unconfirmed = {_text(term) for term in self._values(subject, MIGRATION + 'unconfirmedField')}
        ports = [term.value for term in self._values(subject, ONTOLOGY + 'hasPort')
                 if term.kind == 'uri' and term.value.startswith(self._resource_prefix('port'))]
        for table, sources in (('station', (subject,)), ('port', ports)):
            for column in _RECORDED_FIELDS[table]:
                predicate = _recorded_predicate(TABLES[table][2][column])
                if any(self._values(source, predicate) for source in sources):
                    unconfirmed.add(column)
        evidence['unconfirmedFields'] = sorted(unconfirmed)
        item = normalize_stations({station_id: evidence})[station_id]
        return StationMetadata(
            timezone=item['timezone'],
            hours_completeness=item['hoursCompleteness'],
            ports_completeness=item['portsCompleteness'],
            aggregate_completeness=item['aggregateCompleteness'] or 'INCOMPLETE',
            source_label=item['sourceLabel'],
            source_updated_at=item['sourceUpdatedAt'],
            unconfirmed_fields=tuple(item['unconfirmedFields']),
        )
