import json
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs

import pytest

from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError, NotReadyError
from ca.uvic.ecs.csc501.dal.settings import Settings


GRAPH = 'https://example.test/graph/preview/'
VEHICLE = 'https://example.test/data/vehicle-1'
OTHER_VEHICLE = 'https://example.test/data/vehicle-2'
RESULT_FORMAT = 'application/sparql-results+json'


@pytest.fixture
def endpoint():
    requests = []
    responses = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            data = self.rfile.read(int(self.headers['Content-Length'])).decode('ascii')
            requests.append((self.path, self.headers['Accept'], parse_qs(data)))
            status, body = responses.pop(0)
            self.send_response(status)
            self.send_header('Content-Type', RESULT_FORMAT)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}/sparql', requests, responses
        finally:
            server.shutdown()
            thread.join()


def semantic_repository(endpoint_url, graph=GRAPH):
    from ca.uvic.ecs.csc501.dal.semantic.repository import VirtuosoSemanticRepository

    return VirtuosoSemanticRepository(endpoint_url, graph)


def uri(value):
    return {'type': 'uri', 'value': value}


def literal(value, **kwargs):
    return {'type': 'literal', 'value': value, **kwargs}


def select_response(variables, *rows):
    return 200, json.dumps({'head': {'vars': variables}, 'results': {'bindings': rows}}).encode('utf-8')


def test_fast_chargers_query_configured_graph_and_preserve_power_evidence(endpoint):
    endpoint_url, requests, responses = endpoint
    variables = ['station', 'stationName', 'port', 'powerKw', 'connectorName',
                 'powerEvidenceScope', 'powerEvidenceSource', 'powerEvidenceCheckedOn']
    source_url = 'https://example.test/station/1'
    responses.append(select_response(variables, {
        'station': uri('https://example.test/data/station-1'),
        'stationName': literal('충전소'),
        'port': uri('https://example.test/data/port-1'),
        'powerKw': literal('250.0', datatype='http://www.w3.org/2001/XMLSchema#decimal'),
        'connectorName': literal('NACS'),
        'powerEvidenceScope': literal('Published charging group maximum'),
        'powerEvidenceSource': uri(source_url),
        'powerEvidenceCheckedOn': literal('2026-11-15', datatype='http://www.w3.org/2001/XMLSchema#date'),
    }, {
        'station': uri('https://example.test/data/station-2'),
        'port': uri('https://example.test/data/port-2'),
        'powerKw': literal('150.0', datatype='http://www.w3.org/2001/XMLSchema#decimal'),
        'connectorName': literal('CCS1'),
        'powerEvidenceScope': literal('Port rating'),
    }))

    results = semantic_repository(endpoint_url).fast_chargers()

    from ca.uvic.ecs.csc501.cmn.contracts.semantic import HighPowerPort

    assert results == [
        HighPowerPort('충전소', Decimal('250.0'), 'NACS', 'Published charging group maximum', source_url, '2026-11-15'),
        HighPowerPort(None, Decimal('150.0'), 'CCS1', 'Port rating', None, None),
    ]
    path, accept, params = requests[0]
    assert path == '/sparql'
    assert accept == RESULT_FORMAT
    assert params['format'] == [RESULT_FORMAT]
    query, = params['query']
    assert f'GRAPH <{GRAPH}>' in query
    assert query.count('SELECT ') == 1
    assert 'FILTER (STR(?currentType) = "DC" && ?powerKw > 100)' in query


def test_vehicle_choices_select_only_graph_iri_and_optional_model(endpoint):
    endpoint_url, requests, responses = endpoint
    responses.append(select_response(['vehicle', 'model'], {'vehicle': uri(OTHER_VEHICLE)}, {
        'vehicle': uri(VEHICLE), 'model': literal('Demonstration vehicle'),
    }))

    results = semantic_repository(endpoint_url).vehicles()

    from ca.uvic.ecs.csc501.cmn.contracts.semantic import SemanticVehicle

    assert results == [SemanticVehicle(OTHER_VEHICLE, None), SemanticVehicle(VEHICLE, 'Demonstration vehicle')]
    query, = requests[0][2]['query']
    assert f'GRAPH <{GRAPH}>' in query
    assert 'SELECT DISTINCT ?vehicle ?model' in query
    assert 'ORDER BY ?model ?vehicle' in query
    assert 'VIN' not in query.upper()


def test_adapter_candidates_query_selected_vehicle_and_hide_non_web_evidence(endpoint):
    endpoint_url, requests, responses = endpoint
    variables = ['station', 'stationName', 'port', 'vehicle', 'vehicleModel', 'adapter',
                 'adapterModel', 'fromName', 'toName', 'portCurrent', 'adapterCurrent', 'adapterSource']
    rows = {
        'station': uri('https://example.test/data/station-1'),
        'stationName': literal('Sample station'),
        'port': uri('https://example.test/data/port-1'),
        'vehicle': uri(VEHICLE),
        'vehicleModel': literal('Demonstration vehicle'),
        'adapter': uri('https://example.test/data/adapter-1'),
        'adapterModel': literal('Catalogue model A'),
        'fromName': literal('CHAdeMO'),
        'toName': literal('CCS1'),
        'adapterCurrent': literal('DC'),
        'adapterSource': literal('urn:unpublished:source'),
    }
    source_url = 'http://example.test/catalogue/adapter-2'
    responses.append(select_response(variables, rows, {
        **rows,
        'adapter': uri('https://example.test/data/adapter-2'),
        'adapterModel': literal('Catalogue model B'),
        'adapterSource': literal(source_url),
        'portCurrent': literal('DC'),
    }))

    results = semantic_repository(endpoint_url).adapter_candidates(VEHICLE)

    from ca.uvic.ecs.csc501.cmn.contracts.semantic import AdapterCandidate

    assert results == [
        AdapterCandidate('Sample station', 'Catalogue model A', 'CHAdeMO', 'CCS1', None, None, adapter_current='DC'),
        AdapterCandidate('Sample station', 'Catalogue model B', 'CHAdeMO', 'CCS1', 'DC', source_url, adapter_current='DC'),
    ]
    query, = requests[0][2]['query']
    assert f'GRAPH <{GRAPH}>' in query
    assert f'VALUES ?vehicle {{ <{VEHICLE}> }}' in query
    assert 'HAVING (MAX(?alreadyDirect) = 0)' in query


def test_semantic_settings_preserve_encoded_iris(tmp_path):
    (tmp_path / 'config.properties').write_text(
        '[semantic]\nsparql_endpoint=http://localhost:8890/plugged%20in/sparql\n'
        'graph_iri=https://example.test/graph/BC%20Stations\n', encoding='utf-8',
    )

    settings = Settings(dal_root=tmp_path)

    assert settings.sparql_endpoint == 'http://localhost:8890/plugged%20in/sparql'
    assert settings.sparql_graph == 'https://example.test/graph/BC%20Stations'


@pytest.mark.parametrize('vehicle', ['relative/path', 'https://example.test/invalid>iri', 'https://example.test/with space'])
def test_invalid_vehicle_iri_is_rejected_before_querying(endpoint, vehicle):
    endpoint_url, requests, _ = endpoint

    with pytest.raises(InputError):
        semantic_repository(endpoint_url).adapter_candidates(vehicle)

    assert not requests


def test_invalid_graph_iri_is_rejected_before_querying(endpoint):
    endpoint_url, requests, _ = endpoint

    with pytest.raises(NotReadyError):
        semantic_repository(endpoint_url, 'https://example.test/invalid>graph').fast_chargers()

    assert not requests


@pytest.mark.parametrize('response', [
    (503, b''),
    (200, b'not JSON'),
    (200, b'{"head":{"vars":["vehicle","model"]},"results":{"bindings":{}}}'),
    select_response(['vehicle', 'model'], {'vehicle': literal(VEHICLE)}),
])
def test_endpoint_errors_and_malformed_results_are_reported_as_not_ready(endpoint, response):
    endpoint_url, _, responses = endpoint
    responses.append(response)

    with pytest.raises(NotReadyError, match='Semantic'):
        semantic_repository(endpoint_url).vehicles()


def test_empty_results_are_available(endpoint):
    endpoint_url, _, responses = endpoint
    responses.append(select_response(['vehicle', 'model']))

    assert semantic_repository(endpoint_url).vehicles() == []
