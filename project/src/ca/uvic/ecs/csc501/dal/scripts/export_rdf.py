"""Export a read-only SQLite snapshot as RDF/XML instance data for Virtuoso."""

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
from xml.etree import ElementTree as ET

from ..metadata import read_metadata
from ..semantic.rdf import Dataset, MIGRATION, ONTOLOGY, RDF, RELATIONS, TABLES, Triple
from ..settings import Settings


def source_triples(settings: Settings, *, dataset: str) -> tuple[set[Triple], dict[str, int]]:
    """Read the original schema and station metadata without changing the source."""
    codec = Dataset(dataset)
    triples = set()
    counts = {}
    metadata = read_metadata(settings)

    with closing(sqlite3.connect(settings.database_path.as_uri() + '?mode=ro', uri=True,
                                 timeout=settings.busy_timeout_ms / 1000)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute('BEGIN')
        if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise ValueError('The source database has broken foreign key references.')

        for table, (_, key, fields) in TABLES.items():
            rows = connection.execute(f'SELECT * FROM "{table}" ORDER BY "{key}"')
            expected = {key, *fields, *RELATIONS.get(table, {})}
            if {column[0] for column in rows.description} != expected:
                raise ValueError(f'Source columns do not match the RDF mapping for {table}.')
            counts[table] = 0
            for row in rows:
                evidence = metadata.get(str(row['station_id'])) if table in ('station', 'port') else None
                triples.update(codec.encode(table, dict(row), evidence=evidence))
                counts[table] += 1
    return triples, counts


def _name(namespace, local_name):
    return f'{{{namespace}}}{local_name}'


def export_rdf(settings: Settings, output_path: Path, *, dataset: str) -> dict[str, int]:
    """Write a new RDF/XML file and return source counts for all 13 tables."""
    triples, counts = source_triples(settings, dataset=dataset)
    ET.register_namespace('rdf', RDF)
    ET.register_namespace('plug', ONTOLOGY)
    ET.register_namespace('migration', MIGRATION)
    document = ET.Element(_name(RDF, 'RDF'))
    nodes = {}

    ordered = sorted(triples, key=lambda triple: (triple[0], triple[1], triple[2].sparql()))
    for subject, predicate, term in ordered:
        if subject not in nodes:
            nodes[subject] = ET.SubElement(document, _name(RDF, 'Description'), {_name(RDF, 'about'): subject})
        namespace = next(namespace for namespace in (RDF, ONTOLOGY, MIGRATION) if predicate.startswith(namespace))
        name = _name(namespace, predicate.removeprefix(namespace))
        if term.kind == 'uri':
            ET.SubElement(nodes[subject], name, {_name(RDF, 'resource'): term.value})
        else:
            ET.SubElement(nodes[subject], name, {_name(RDF, 'datatype'): term.datatype}).text = term.value

    ET.indent(document)
    # Preserve literal carriage returns through XML end-of-line normalization.
    rdf_bytes = ET.tostring(document, encoding='utf-8', xml_declaration=True).replace(b'\r', b'&#13;')
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
