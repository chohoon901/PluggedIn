"""Server-rendered charging query behavior with a controlled graph repository."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from ca.uvic.ecs.csc501.cmn.contracts.errors import NotReadyError
from ca.uvic.ecs.csc501.cmn.contracts.semantic import AdapterCandidate, HighPowerPort, SemanticVehicle
from ca.uvic.ecs.csc501.dal.database import Database
from ca.uvic.ecs.csc501.dal.settings import Settings
from ca.uvic.ecs.csc501.main import create_app


VAN_IRI = 'https://example.test/vehicles/van'
EMPTY_IRI = 'https://example.test/vehicles/empty'
POWER_SOURCE = 'https://example.test/evidence/kaslo'
ADAPTER_SOURCE = 'https://example.test/catalogue/adapter'


class GraphRepository:
    def fast_chargers(self):
        return [
            HighPowerPort(
                'Kaslo', Decimal('180'), 'CCS1',
                'Charging group maximum advertised by operator', POWER_SOURCE, '2026-11-19',
            ),
            HighPowerPort('River Station', Decimal('125.5'), 'CHAdeMO', 'Port rating', None, None),
        ]

    def vehicles(self):
        return [SemanticVehicle(VAN_IRI, 'Demo Van'), SemanticVehicle(EMPTY_IRI, 'Demo Car')]

    def adapter_candidates(self, vehicle_iri):
        if vehicle_iri != VAN_IRI:
            return []
        return [AdapterCandidate('River Station', 'Demo adapter', 'NACS', 'CCS1', 'DC', ADAPTER_SOURCE)]


@pytest.fixture
def client(tmp_path):
    db = Database(Settings(dal_root=tmp_path))
    with TestClient(create_app(db, semantic_repository=GraphRepository())) as http:
        yield http
    db.engine.dispose()


def test_fast_charging_page_shows_power_scope_and_provenance(client):
    response = client.get('/semantic')

    assert response.status_code == 200
    assert 'Kaslo' in response.text
    assert 'CCS1' in response.text
    assert '180 kW' in response.text
    assert 'Operator-published group maximum' in response.text
    assert f'href="{POWER_SOURCE}"' in response.text
    assert '<time datetime="2026-11-19">2026-11-19</time>' in response.text
    assert '125.5 kW' in response.text
    assert 'Port rating' in response.text
    assert 'Demo adapter' not in response.text


def test_selected_vehicle_shows_connector_candidate_in_server_html(client):
    response = client.get('/semantic', params={'vehicle_iri': VAN_IRI})

    assert response.status_code == 200
    assert '<form method="get"' in response.text
    assert 'name="vehicle_iri"' in response.text
    assert f'value="{VAN_IRI}" selected' in response.text
    assert 'Demo adapter' in response.text
    assert 'NACS → CCS1' in response.text
    assert 'Connector-based adapter candidate' in response.text
    assert 'Port: DC' in response.text
    assert 'Adapter: Unknown' in response.text
    assert f'href="{ADAPTER_SOURCE}"' in response.text


def test_unknown_vehicle_preserves_input_and_choices_on_bad_request(client):
    unknown_iri = 'https://example.test/vehicles/unknown'

    response = client.get('/semantic', params={'vehicle_iri': unknown_iri})

    assert response.status_code == 400
    assert response.headers['content-type'].startswith('text/html')
    assert f'value="{unknown_iri}" selected' in response.text
    assert f'value="{VAN_IRI}"' in response.text
    assert 'Select a vehicle from the list.' in response.text
    assert 'Demo adapter' not in response.text


def test_empty_graph_results_are_successful(client, monkeypatch):
    monkeypatch.setattr(GraphRepository, 'fast_chargers', lambda self: [])

    response = client.get('/semantic', params={'vehicle_iri': EMPTY_IRI})

    assert response.status_code == 200
    assert 'No DC charging results above 100 kW.' in response.text
    assert 'No connector-based adapter candidates found for this vehicle.' in response.text


def test_unavailable_graph_returns_an_html_service_error(client, monkeypatch):
    def unavailable(self):
        raise NotReadyError('The charging graph is temporarily unavailable.')

    monkeypatch.setattr(GraphRepository, 'fast_chargers', unavailable)

    response = client.get('/semantic')

    assert response.status_code == 503
    assert response.headers['content-type'].startswith('text/html')
    assert 'The charging graph is temporarily unavailable.' in response.text
    assert 'No DC charging results above 100 kW.' not in response.text
