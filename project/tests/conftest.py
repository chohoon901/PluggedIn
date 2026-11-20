"""Portable selected-source fixtures: no dependency on untracked full downloads."""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class _GraphSnapshot:
    triples: frozenset


class _MemoryGraphStore:
    dataset = 'fixture'
    graph = 'https://example.test/graph/application/'
    client = None

    def __init__(self, triples):
        self.snapshot = _GraphSnapshot(frozenset(triples))

    def load(self):
        return self.snapshot

    def health(self):
        return True

    def require_ready(self):
        pass

    def commit(self, snapshot, removed, added):
        from ca.uvic.ecs.csc501.cmn.contracts.errors import ConflictError

        if snapshot is not self.snapshot:
            raise ConflictError('The graph changed.')
        self.snapshot = _GraphSnapshot((snapshot.triples - removed) | added)
        return self.snapshot


@pytest.fixture
def rdf_store():
    from ca.uvic.ecs.csc501.dal.scripts.export_rdf import source_triples

    def from_database(database):
        triples, _ = source_triples(database.settings, dataset=_MemoryGraphStore.dataset)
        return _MemoryGraphStore(triples)

    return from_database


@pytest.fixture
def imported_app(rdf_store):
    from ca.uvic.ecs.csc501.cmn.application.services import ApplicationService
    from ca.uvic.ecs.csc501.dal.semantic.unit_of_work import VirtuosoUnitOfWork
    from ca.uvic.ecs.csc501.main import create_app

    def from_database(database):
        store = rdf_store(database)
        services = ApplicationService(lambda: VirtuosoUnitOfWork(store), store.health)
        return create_app(services=services)

    return from_database


@pytest.fixture
def sample_sources(tmp_path):
    manifest_path = (Path(__file__).resolve().parents[1] / 'src/ca/uvic/ecs/csc501/dal/data/sample20/source_manifest.json')
    stations = json.loads(manifest_path.read_text(encoding='utf-8'))['stations']
    csv_path, ocm_path = tmp_path / 'nlr.csv', tmp_path / 'ocm.json'
    with csv_path.open('w', encoding='cp1252', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stations[0]['nlr']))
        writer.writeheader()
        writer.writerows(item['nlr'] for item in stations)
    ocm_path.write_text(json.dumps([item['ocm'] for item in stations]), encoding='utf-8')
    return csv_path, ocm_path
