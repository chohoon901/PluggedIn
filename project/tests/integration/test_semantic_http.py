"""Server-rendered charging query behavior with a controlled graph repository."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from ca.uvic.ecs.csc501.cmn.contracts.errors import NotReadyError
from ca.uvic.ecs.csc501.cmn.contracts.semantic import AdapterCandidate, HighPowerPort, SemanticVehicle
from ca.uvic.ecs.csc501.main import create_app


VAN_IRI = 'https://example.test/vehicles/van'
EMPTY_IRI = 'https://example.test/vehicles/empty'
POWER_SOURCE = 'https://example.test/evidence/kaslo'
ADAPTER_SOURCE = 'https://example.test/catalogue/adapter'


class GraphRepository:
    def fast_chargers(self, min_power_kw):
        ports = [
            HighPowerPort(
                'Kaslo', Decimal('180'), 'CCS1',
                'Charging group maximum advertised by operator', POWER_SOURCE, '2026-11-19',
            ),
            HighPowerPort('River Station', Decimal('125.5'), 'CHAdeMO', 'Port rating', None, None),
        ]
        return [port for port in ports if port.power_kw >= min_power_kw]

    def vehicles(self):
        return [SemanticVehicle(VAN_IRI, 'Demo Van'), SemanticVehicle(EMPTY_IRI, 'Demo Car')]

    def adapter_candidates(self, vehicle_iri):
        if vehicle_iri != VAN_IRI:
            return []
        return [AdapterCandidate(
            'River Station', 'Demo adapter', 'NACS', 'CCS1', 'DC', ADAPTER_SOURCE,
            station_street='4 River Road', station_city='Vancouver',
        )]


@pytest.fixture
def client():
    with TestClient(create_app(semantic_repository=GraphRepository())) as http:
        yield http


def test_fast_charging_page_starts_with_just_the_power_filter(client):
    response = client.get('/fast-charging')

    assert response.status_code == 200
    assert 'name="min_power_kw"' in response.text
    assert 'name="vehicle_iri"' not in response.text
    assert 'Kaslo' not in response.text


def test_fast_charging_results_include_the_requested_threshold_and_provenance(client):
    response = client.get('/fast-charging', params={'min_power_kw': '125.5'})

    assert response.status_code == 200
    assert 'Kaslo' in response.text
    assert 'CCS1' in response.text
    assert '180 kW' in response.text
    assert 'Operator-published group maximum' in response.text
    assert f'href="{POWER_SOURCE}"' in response.text
    assert '<time datetime="2026-11-19">2026-11-19</time>' in response.text
    assert '125.5 kW' in response.text
    assert 'Port rating' in response.text


def test_raising_the_power_filter_removes_lower_rated_results(client):
    response = client.get('/fast-charging', params={'min_power_kw': '126'})

    assert response.status_code == 200
    assert 'value="126"' in response.text
    assert 'Kaslo' in response.text
    assert 'River Station' not in response.text


@pytest.mark.parametrize('minimum', ['', '-1', 'NaN', '1e9999999', '125 } UNION {'])
def test_invalid_power_preserves_the_input_without_querying_the_graph(client, monkeypatch, minimum):
    def unexpected_query(self, min_power_kw):
        pytest.fail('An invalid threshold must not reach the graph.')

    monkeypatch.setattr(GraphRepository, 'fast_chargers', unexpected_query)
    response = client.get('/fast-charging', params={'min_power_kw': minimum})

    assert response.status_code == 400
    assert response.headers['content-type'].startswith('text/html')
    assert f'value="{minimum}"' in response.text
    assert 'aria-invalid="true"' in response.text


def test_selected_vehicle_shows_connector_candidate_in_server_html(client):
    response = client.get('/adapter-finder', params={'vehicle_iri': VAN_IRI})

    assert response.status_code == 200
    assert '<form method="get"' in response.text
    assert 'name="vehicle_iri"' in response.text
    assert 'name="min_power_kw"' not in response.text
    assert f'value="{VAN_IRI}" selected' in response.text
    assert 'Demo adapter' in response.text
    assert 'NACS → CCS1' in response.text
    assert '4 River Road, Vancouver' in response.text
    assert 'Port: DC' in response.text
    assert 'Adapter: Unknown' in response.text
    assert f'href="{ADAPTER_SOURCE}"' in response.text


def test_unknown_vehicle_preserves_input_and_choices_on_bad_request(client):
    unknown_iri = 'https://example.test/vehicles/unknown'

    response = client.get('/adapter-finder', params={'vehicle_iri': unknown_iri})

    assert response.status_code == 400
    assert response.headers['content-type'].startswith('text/html')
    assert f'value="{unknown_iri}" selected' in response.text
    assert f'value="{VAN_IRI}"' in response.text
    assert 'Select a vehicle from the list.' in response.text
    assert 'Demo adapter' not in response.text


def test_no_fast_charger_meets_the_requested_threshold(client):
    response = client.get('/fast-charging', params={'min_power_kw': '181'})

    assert response.status_code == 200
    assert 'No DC charging ports are rated at 181 kW or higher.' in response.text


def test_vehicle_without_a_candidate_shows_an_empty_result(client):
    response = client.get('/adapter-finder', params={'vehicle_iri': EMPTY_IRI})

    assert response.status_code == 200
    assert 'No connector-based adapter candidates found for this vehicle.' in response.text


def test_legacy_query_link_preserves_the_selected_vehicle(client):
    response = client.get('/semantic', params={'vehicle_iri': VAN_IRI})

    assert response.url.path == '/adapter-finder'
    assert response.url.params['vehicle_iri'] == VAN_IRI
    assert 'Demo adapter' in response.text


def test_unavailable_graph_returns_an_html_service_error(client, monkeypatch):
    def unavailable(self, min_power_kw):
        raise NotReadyError('The charging graph is temporarily unavailable.')

    monkeypatch.setattr(GraphRepository, 'fast_chargers', unavailable)

    response = client.get('/fast-charging', params={'min_power_kw': '100'})

    assert response.status_code == 503
    assert response.headers['content-type'].startswith('text/html')
    assert 'The charging graph is temporarily unavailable.' in response.text
    assert 'No DC charging ports' not in response.text
