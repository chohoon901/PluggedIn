from contextlib import closing
from datetime import date
from decimal import Decimal
import json
import sqlite3
from xml.etree import ElementTree

import pytest

from ca.uvic.ecs.csc501.cmn.domain.value_objects.daily_time import DailyTime
from ca.uvic.ecs.csc501.dal.database import Database
from ca.uvic.ecs.csc501.dal.scripts.init_db import init_database
from ca.uvic.ecs.csc501.dal.scripts.seed_demo import seed_demo
from ca.uvic.ecs.csc501.dal.settings import Settings


def test_sqlite_snapshot_decodes_all_columns_and_matches_rdf_xml(tmp_path):
    from ca.uvic.ecs.csc501.dal.scripts.export_rdf import export_rdf, source_triples
    from ca.uvic.ecs.csc501.dal.semantic.rdf import Dataset, MIGRATION, ONTOLOGY, RDF, Term

    settings = Settings(tmp_path)
    database = Database(settings)
    init_database(database)
    seed_demo(database)
    with closing(sqlite3.connect(settings.database_path)) as connection:
        connection.execute("INSERT INTO adapter VALUES (8, 'Fictional', '제조사', 78.5, 1, 2)")
        connection.execute('UPDATE driver SET name = ? WHERE driver_id = 1', ('운전자 \"민아\"\r\n<팀>',))
        connection.execute("UPDATE membership SET end_date = '2026-12-31' WHERE membership_id = 1")
        connection.execute('UPDATE connector_type SET max_power_kw = 375.5 WHERE connector_type_id = 1')
        connection.commit()

    metadata = json.loads(settings.metadata_path.read_text(encoding='utf-8'))
    del metadata['stations']['5']
    settings.metadata_path.write_text(json.dumps(metadata), encoding='utf-8')

    triples, counts = source_triples(settings, dataset='round-trip')
    dataset = Dataset('round-trip', triples)
    assert len(counts) == 13
    assert all(counts.values())
    column_count = 0
    with closing(sqlite3.connect(settings.database_path)) as connection:
        connection.row_factory = sqlite3.Row
        for table, count in counts.items():
            columns = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            column_count += len(columns)
            key = next(column['name'] for column in columns if column['pk'])
            expected = {}
            for source in connection.execute(f'SELECT * FROM "{table}"'):
                row = dict(source)
                for column in columns:
                    name, datatype = column['name'], column['type']
                    value = row[name]
                    if value is None:
                        continue
                    if datatype.startswith('NUMERIC'):
                        row[name] = Decimal(str(value))
                    elif datatype == 'DATE':
                        row[name] = date.fromisoformat(value)
                    elif name in {'open_time', 'close_time'}:
                        row[name] = DailyTime.parse(value)
                    elif name in {'accepts_guest_payment', 'has_truck_parking'}:
                        row[name] = bool(value)
                expected[row[key]] = row
            records = dataset.records(table)
            assert len(records) == count
            assert records == expected, table
    assert column_count == 65
    assert type(dataset.records('vehicle')[1]['range_km']) is int
    assert dataset.records('station')[5]['accepts_guest_payment'] is True
    assert dataset.station_evidence(1).timezone == 'America/Vancouver'
    assert dataset.station_evidence(5).hours_completeness == 'UNKNOWN'
    assert set(dataset.station_evidence(5).unconfirmed_fields) == {
        'accepts_guest_payment', 'has_truck_parking', 'power_kw', 'quantity',
    }
    port_predicates = {predicate for subject, predicate, _ in triples if subject == dataset.resource('port', 5)}
    assert ONTOLOGY + 'powerKw' not in port_predicates
    assert MIGRATION + 'recordedPowerKw' in port_predicates

    output = tmp_path / 'export.rdf'
    assert export_rdf(settings, output, dataset='round-trip') == counts
    xml_triples = set()
    for node in ElementTree.parse(output).getroot():
        for element in node:
            namespace, local = element.tag[1:].split('}', 1)
            target = element.get(f'{{{RDF}}}resource')
            term = Term(target, 'uri') if target else Term(element.text or '', datatype=element.get(f'{{{RDF}}}datatype'))
            xml_triples.add((node.attrib[f'{{{RDF}}}about'], namespace + local, term))
    assert xml_triples == triples


def test_sparql_terms_preserve_unicode_language_and_datatype():
    from ca.uvic.ecs.csc501.dal.semantic.rdf import Term, XSD, iri_ref, sparql_triples

    text = '민아 "EV"\r\n\\ next\t'
    term = Term.from_binding({'type': 'literal', 'value': text, 'xml:lang': 'ko-KR'})
    assert term == Term(text, language='ko-KR')
    decimal = Term.from_binding({'type': 'typed-literal', 'value': '12.0', 'datatype': XSD + 'decimal'})
    assert decimal == Term('12.0', datatype=XSD + 'decimal')
    assert sparql_triples({('urn:test:s', 'urn:test:p', term), ('urn:test:s', 'urn:test:p', decimal)}) == (
        '<urn:test:s> <urn:test:p> "12.0"^^<http://www.w3.org/2001/XMLSchema#decimal> .\n'
        '<urn:test:s> <urn:test:p> "민아 \\"EV\\"\\r\\n\\\\ next\\t"@ko-KR .'
    )
    with pytest.raises(ValueError):
        iri_ref('https://example.invalid/> DROP ALL')
    for binding in (
        {'type': 'bnode', 'value': 'anon'},
        {'type': 'uri', 'value': 'relative'},
        {'type': 'literal', 'value': 42},
        {'type': 'literal', 'value': 'a', 'xml:lang': 'ko .'},
        {'type': 'literal', 'value': 'a', 'datatype': 'urn:type', 'xml:lang': 'ko'},
        {'type': 'typed-literal', 'value': 'a'},
    ):
        with pytest.raises(ValueError):
            Term.from_binding(binding)


def test_mutable_record_triples_keep_unrelated_facts_and_detect_ambiguous_rows():
    from ca.uvic.ecs.csc501.dal.semantic.rdf import Dataset, MIGRATION, ONTOLOGY, Term

    dataset = Dataset('profiles')
    membership = {'membership_id': 7, 'driver_id': 4, 'network_id': 9, 'start_date': date(2026, 1, 1)}
    driver = dataset.encode('driver', {'driver_id': 4, 'licence_number': 'DEMO-4', 'name': '나무'})
    vehicle = dataset.encode('vehicle', {'vehicle_id': 2, 'vin': 'DEMO0000000000001'})
    joins = dataset.encode('vehicle_accepts', {'vehicle_accepts_id': 2, 'vehicle_id': 2, 'connector_type_id': 8})
    changed_membership = {
        (subject, predicate, Term(term.value) if predicate == ONTOLOGY + 'startDate' else term)
        for subject, predicate, term in dataset.encode('membership', membership)
    }
    elsewhere = Dataset('different-dataset')
    extras = {
        (dataset.resource('driver', 4), MIGRATION + 'annotation', Term('남겨 두는 메모', language='ko')),
        (dataset.resource('vehicle', 2), ONTOLOGY + 'vehicleAccepts', Term(elsewhere.resource('connector_type', 5), 'uri')),
        (elsewhere.resource('driver', 3), ONTOLOGY + 'hasMembership', Term(dataset.resource('membership', 7), 'uri')),
    }
    triples = driver | vehicle | joins | changed_membership | extras
    loaded = Dataset('profiles', triples)
    assert loaded.record_triples('driver', 4) == driver
    assert loaded.record_triples('vehicle', 2) == vehicle
    assert loaded.record_triples('vehicle_accepts', 2) == joins
    assert loaded.record_triples('membership', 7) == changed_membership
    assert loaded.record_triples('driver', 5) == set()
    assert loaded.records('membership') == {7: {**membership, 'end_date': None}}

    conflicting_owner = dataset.resource('driver', 8), ONTOLOGY + 'hasMembership', Term(dataset.resource('membership', 7), 'uri')
    with pytest.raises(ValueError):
        Dataset('profiles', triples | {conflicting_owner}).records('membership')
