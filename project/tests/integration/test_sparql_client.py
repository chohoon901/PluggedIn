from base64 import b64encode
from hashlib import md5
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from traceback import format_exception
from urllib.parse import parse_qs
from urllib.request import parse_http_list, parse_keqv_list

import pytest

from ca.uvic.ecs.csc501.cmn.contracts.errors import NotReadyError
from ca.uvic.ecs.csc501.cmn.contracts.semantic import SemanticVehicle
from ca.uvic.ecs.csc501.dal.semantic.client import SparqlClient
from ca.uvic.ecs.csc501.dal.semantic.repository import VirtuosoSemanticRepository


GRAPH = 'https://example.test/graph/'
USERNAME = 'test-publisher'
PASSWORD = 'test-password'
RESULT_FORMAT = 'application/sparql-results+json'


@pytest.fixture
def service():
    requests = []
    responses = []

    class Handler(BaseHTTPRequestHandler):
        def _respond(self):
            content = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            requests.append((self.command, self.path, self.headers, content))
            status, headers, body = responses.pop(0)
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_POST = _respond
        do_GET = _respond

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}/sparql-auth', requests, responses
        finally:
            server.shutdown()
            thread.join()


def authenticated_client(endpoint):
    return SparqlClient(endpoint, username=USERNAME, password=PASSWORD)


def test_update_resends_the_form_with_a_valid_digest(service):
    endpoint, requests, responses = service
    challenge = ('Digest realm="virtuoso", domain="/sparql-auth", nonce="test-nonce", '
                 'opaque="test-opaque", stale="false", qop="auth", algorithm="MD5"')
    responses.extend([(401, {'WWW-Authenticate': challenge}, b''), (204, {}, b'')])
    query = f'INSERT DATA {{ GRAPH <{GRAPH}> {{ <urn:s> <urn:p> "충전" }} }}'

    authenticated_client(endpoint).update(query)

    first, second = requests
    assert first[2].get('Authorization') is None
    method, path, headers, body = second
    assert method == 'POST'
    assert path == '/sparql-auth'
    assert headers.get_content_type() == 'application/x-www-form-urlencoded'
    assert body == first[3]
    assert parse_qs(body.decode('ascii'))['query'] == [query]

    scheme, params = headers['Authorization'].split(' ', 1)
    terms = parse_keqv_list(parse_http_list(params))
    assert scheme == 'Digest'
    assert terms['username'] == USERNAME
    assert terms['uri'] == path
    assert terms['opaque'] == 'test-opaque'
    assert terms['qop'] == 'auth'
    assert terms['nc'] == '00000001'
    identity = md5(f'{USERNAME}:virtuoso:{PASSWORD}'.encode(), usedforsecurity=False).hexdigest()
    request = md5(b'POST:/sparql-auth', usedforsecurity=False).hexdigest()
    proof = f'{identity}:test-nonce:00000001:{terms["cnonce"]}:auth:{request}'
    assert terms['response'] == md5(proof.encode(), usedforsecurity=False).hexdigest()


def test_cq_uses_the_supplied_authenticated_client(service):
    endpoint, requests, responses = service
    responses.extend([
        (401, {'WWW-Authenticate': 'Basic realm="local-gateway"'}, b''),
        (200, {'Content-Type': RESULT_FORMAT},
         b'{"head":{"vars":["vehicle"]},"results":{"bindings":['
         b'{"vehicle":{"type":"uri","value":"urn:vehicle:1"}}]}}'),
    ])
    repository = VirtuosoSemanticRepository('https://unused.invalid/sparql', GRAPH,
                                             client=authenticated_client(endpoint))

    assert repository.vehicles() == [SemanticVehicle('urn:vehicle:1', None)]

    first, second = requests
    assert first[2].get('Authorization') is None
    headers, body = second[2:]
    encoded = b64encode(f'{USERNAME}:{PASSWORD}'.encode()).decode('ascii')
    assert headers['Authorization'] == f'Basic {encoded}'
    assert headers['Accept'] == '*/*'
    params = parse_qs(body.decode('ascii'))
    assert params['format'] == [RESULT_FORMAT]
    assert f'GRAPH <{GRAPH}>' in params['query'][0]


@pytest.mark.parametrize(('body', 'expected'), [(b'true', True), (b'false', False)])
def test_ask_preserves_a_boolean_response(service, body, expected):
    endpoint, _, responses = service
    responses.append((200, {'Content-Type': RESULT_FORMAT}, b'{"boolean":' + body + b'}'))

    assert authenticated_client(endpoint).ask('ASK { ?s a <urn:entity> }') is expected


@pytest.mark.parametrize(('value', 'expected'), [(b'0', False), (b'1', True)])
def test_virtuoso_integer_ask_results(service, value, expected):
    endpoint, _, responses = service
    payload = (
        b'{"head":{"vars":["__ASK_RETVAL"]},"results":{"bindings":[{"__ASK_RETVAL":'
        b'{"type":"literal","datatype":"http://www.w3.org/2001/XMLSchema#integer","value":"'
        + value + b'"}}]}}'
    )
    responses.append((200, {'Content-Type': RESULT_FORMAT}, payload))

    assert authenticated_client(endpoint).ask('ASK { ?s a <urn:entity> }') is expected


@pytest.mark.parametrize(('status', 'headers', 'body'), [
    (200, {}, b'{"boolean":"false"}'),
    (206, {}, b'{"boolean":false}'),
    (200, {'X-SQL-State': 'S1TAT'}, b'{"boolean":false}'),
])
def test_ask_rejects_invalid_or_partial_results(service, status, headers, body):
    endpoint, requests, responses = service
    responses.append((status, headers, body))

    with pytest.raises(NotReadyError):
        authenticated_client(endpoint).ask('ASK { ?s a <urn:entity> }')

    assert len(requests) == 1


def test_authenticated_request_rejects_redirect_without_exposing_details(service):
    endpoint, requests, responses = service
    responses.extend([
        (401, {'WWW-Authenticate': 'Basic realm="local-gateway"'}, b''),
        (302, {'Location': '/another-endpoint'}, b'secret submitted information'),
        (204, {}, b''),
    ])
    query = f'INSERT DATA {{ GRAPH <{GRAPH}> {{ <urn:s> <urn:p> "secret submitted information" }} }}'

    with pytest.raises(NotReadyError) as error:
        authenticated_client(endpoint).update(query)

    assert [(method, path) for method, path, _, _ in requests] == [('POST', '/sparql-auth')] * 2
    details = ''.join(format_exception(error.value))
    for value in (USERNAME, PASSWORD, query, 'secret submitted information', '/another-endpoint'):
        assert value not in details


@pytest.mark.parametrize('endpoint', [
    'http://192.0.2.1/sparql-auth',
    'http://embedded-user:embedded-secret@127.0.0.1:8890/sparql-auth',
])
def test_unsafe_authenticated_endpoints_are_rejected_before_connecting(monkeypatch, endpoint):
    def unexpected_connection(*args, **kwargs):
        raise AssertionError('The invalid URL was used to connect.')

    monkeypatch.setattr('socket.create_connection', unexpected_connection)

    with pytest.raises(NotReadyError) as error:
        authenticated_client(endpoint).ask('ASK { ?s a <urn:entity> }')

    assert 'embedded-secret' not in ''.join(format_exception(error.value))
