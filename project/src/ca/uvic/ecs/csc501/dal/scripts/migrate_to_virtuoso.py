"""Migrate the configured SQLite snapshot into a private Virtuoso graph."""

import argparse
from importlib.resources import files
from pathlib import Path
from sqlite3 import Error as SQLiteError
from urllib.parse import urlsplit

from ...cmn.contracts.errors import AppError, NotReadyError
from ..database import Database
from ..semantic.client import SparqlClient
from ..semantic.rdf import MIGRATION, ONTOLOGY, PROJECT, Dataset, Triple, iri_ref
from ..semantic.store import VirtuosoStore
from ..semantic.unit_of_work import VirtuosoUnitOfWork
from ..settings import Settings
from .export_rdf import source_triples
from .validate_db import validate_database


def _require_credentials(settings: Settings) -> None:
    if not settings.virtuoso_user or not settings.virtuoso_password:
        raise NotReadyError('Set PLUGGEDIN_VIRTUOSO_USER and PLUGGEDIN_VIRTUOSO_PASSWORD.')


def _origin(endpoint: str) -> tuple:
    parts = urlsplit(endpoint)
    hostname = parts.hostname
    if hostname in ('localhost', '127.0.0.1', '::1'):
        hostname = 'loopback'
    return parts.scheme, hostname, parts.port or {'http': 80, 'https': 443}.get(parts.scheme)


def _sample_equipment_update(graph: str) -> str:
    query = files('ca.uvic.ecs.csc501.dal.semantic').joinpath(
        'queries', 'sample20_equipment_evidence.ru',
    ).read_text(encoding='utf-8')
    sample_graph = iri_ref(PROJECT + 'graph/')
    return query.replace(f'GRAPH {sample_graph}', f'GRAPH {iri_ref(graph)}')


def _install_sample_equipment(store: VirtuosoStore, query: str) -> None:
    store.client.update(query)
    proof = f"""
PREFIX plug: <{ONTOLOGY}>
PREFIX migration: <{MIGRATION}>
PREFIX catalog: <{PROJECT}data/catalog/Adapter/>
ASK {{ GRAPH {iri_ref(store.graph)} {{
  <{PROJECT}data/sample20/Port/9> migration:operatorPublishedPowerKw ?power ;
                                migration:powerEvidenceSource ?powerSource .
  FILTER (?power = 250)
  <{PROJECT}data/sample20/Port/12> migration:installedChargerPowerKw 50.0 ;
                                 migration:powerEvidenceSource ?norgateSource .
  <{PROJECT}data/sample20/Port/13> migration:installedChargerPowerKw 50.0 ;
                                 migration:powerEvidenceSource ?norgateSource .
  catalog:ford-vrk9z10e826a migration:adapterEvidence ?fordSource .
  catalog:a2z-stellar-pro migration:adapterEvidence ?stellarSource .
  catalog:a2z-legacy-ccs1 migration:adapterEvidence ?legacySource .
  catalog:tesla-sae-j1772 migration:adapterEvidence ?teslaSource .
}} }}
"""
    if not store.client.ask(proof):
        raise NotReadyError('The sample20 graph is missing power or adapter evidence.')


def _derived_links(triples: set[Triple] | frozenset[Triple]) -> set[tuple[str, str, str]]:
    return {(subject, predicate, obj.value) for subject, predicate, obj in triples
            if predicate in (ONTOLOGY + 'vehicleAccepts', MIGRATION + 'connectorFamily')}


def migrate(settings: Settings) -> dict[str, int]:
    _require_credentials(settings)
    if settings.app_sparql_graph == settings.sparql_graph:
        raise NotReadyError('Choose an application graph separate from the public charging graph.')
    if _origin(settings.app_sparql_endpoint) != _origin(settings.sparql_endpoint):
        raise NotReadyError('The public and authenticated SPARQL endpoints must point to the same Virtuoso server.')

    source = Database(settings, read_only=True)
    try:
        if validate_database(source):
            raise NotReadyError('Validate the SQLite migration source before importing it.')
    finally:
        source.engine.dispose()
    triples, counts = source_triples(settings, dataset=settings.rdf_dataset)
    original = Dataset(settings.rdf_dataset, triples)
    evidence = _sample_equipment_update(settings.app_sparql_graph) if settings.rdf_dataset == 'sample20' else None

    store = VirtuosoStore.from_settings(settings)
    store.initialize(triples, SparqlClient(settings.sparql_endpoint))
    pending = store.load(allow_pending=True)
    installed = Dataset(settings.rdf_dataset, pending.triples)
    for table in counts:
        if installed.records(table) != original.records(table):
            raise NotReadyError(f'Virtuoso did not preserve the imported {table} data.')
    for station_id in original.records('station'):
        if installed.station_evidence(station_id) != original.station_evidence(station_id):
            raise NotReadyError('Virtuoso did not preserve the imported station metadata.')
    if _derived_links(pending.triples) != _derived_links(triples):
        raise NotReadyError('Virtuoso did not preserve the imported connector links.')
    if evidence is not None:
        _install_sample_equipment(store, evidence)
        pending = store.load(allow_pending=True)
    store.finish_import(pending)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dal-root', type=Path, help='Directory containing config.properties')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Check the existing Virtuoso application graph')
    mode.add_argument('--sample-equipment', action='store_true', help='Reapply the sample20 equipment evidence')
    args = parser.parse_args()
    try:
        settings = Settings(args.dal_root)
        _require_credentials(settings)
        if args.check or args.sample_equipment:
            store = VirtuosoStore.from_settings(settings)
            with VirtuosoUnitOfWork(store):
                pass
            if args.sample_equipment:
                if settings.rdf_dataset != 'sample20':
                    raise ValueError('Equipment evidence requires the sample20 dataset.')
                _install_sample_equipment(store, _sample_equipment_update(store.graph))
                print('Sample20 equipment evidence is ready.')
            else:
                print('Virtuoso application graph is ready.')
        else:
            counts = migrate(settings)
            print(f'Verified {sum(counts.values())} SQLite records in the private Virtuoso graph.')
            print(', '.join(f'{table}={count}' for table, count in counts.items()))
    except (AppError, SQLiteError, OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
