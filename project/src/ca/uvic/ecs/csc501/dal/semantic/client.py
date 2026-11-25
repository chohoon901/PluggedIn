"""Send SPARQL queries and updates to Virtuoso."""

import json
import re
from http import HTTPStatus
from http.client import HTTPException
from ipaddress import ip_address
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import (
    BaseHandler,
    HTTPBasicAuthHandler,
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
    build_opener,
)

from ca.uvic.ecs.csc501.cmn.contracts.errors import NotReadyError


_RESULT_FORMAT = 'application/sparql-results+json'
_BAD_RESULTS = 'Semantic data returned an invalid query result.'
_UNAVAILABLE = 'Semantic data is temporarily unavailable.'
_FORBIDDEN_URL_CHARACTERS = re.compile(r'[\x00-\x20\x7f<>"{}|^`\\\ud800-\udfff]|%(?![0-9A-Fa-f]{2})')


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _is_loopback(hostname: str) -> bool:
    if hostname == 'localhost':
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


class SparqlClient:
    def __init__(self, endpoint: str, *, username: str | None = None,
                 password: str | None = None, timeout_seconds: float = 4.0,
                 require_authentication: bool = False):
        self._endpoint = endpoint
        self._username = username
        self._password = password
        self._timeout_seconds = timeout_seconds
        self._require_authentication = require_authentication

    def _opener(self) -> OpenerDirector:
        url = urlsplit(self._endpoint)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username is not None
                or url.fragment or _FORBIDDEN_URL_CHARACTERS.search(self._endpoint)):
            raise ValueError('Invalid SPARQL endpoint.')

        handlers: list[BaseHandler] = [ProxyHandler({}), _RejectRedirects()]
        if self._username is not None or self._password is not None:
            if not self._username or self._password is None:
                raise ValueError('Incomplete SPARQL credentials.')
            if url.scheme == 'http' and not _is_loopback(url.hostname):
                raise ValueError('Authenticated SPARQL requires HTTPS or loopback.')
            passwords = HTTPPasswordMgrWithDefaultRealm()
            passwords.add_password(None, self._endpoint, self._username, self._password)
            handlers.extend((HTTPDigestAuthHandler(passwords), HTTPBasicAuthHandler(passwords)))
        # Digest state belongs to one operation, since callers share this client across requests.
        return build_opener(*handlers)

    def _post(self, query: str, *, expect_json: bool) -> bytes:
        if self._require_authentication and (not self._username or not self._password):
            raise NotReadyError('Configure the Virtuoso application credentials first.')
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        params = {'query': query}
        if expect_json:
            headers['Accept'] = '*/*'
            params['format'] = _RESULT_FORMAT

        try:
            opener = self._opener()
            request = Request(self._endpoint, data=urlencode(params).encode('ascii'), headers=headers, method='POST')
            with opener.open(request, timeout=self._timeout_seconds) as response:
                # Virtuoso can report a partial result with HTTP 200 when configured to do so.
                if response.status == HTTPStatus.PARTIAL_CONTENT or response.headers.get('X-SQL-State') == 'S1TAT':
                    raise NotReadyError(_UNAVAILABLE)
                return response.read() if expect_json else b''
        except HTTPError as error:
            error.close()
            raise NotReadyError(_UNAVAILABLE) from None
        except (OSError, HTTPException, ValueError, OverflowError):
            raise NotReadyError(_UNAVAILABLE) from None

    def _query(self, query: str) -> dict[str, object]:
        response = self._post(query, expect_json=True)
        try:
            payload = json.loads(response)
        except (ValueError, RecursionError):
            raise NotReadyError(_BAD_RESULTS) from None
        if not isinstance(payload, dict):
            raise NotReadyError(_BAD_RESULTS)
        return payload

    def select(self, query: str) -> list[dict[str, object]]:
        return self._result_rows(self._query(query))

    @staticmethod
    def _result_rows(payload: dict[str, object]) -> list[dict[str, object]]:
        head, results = payload.get('head'), payload.get('results')
        if not isinstance(head, dict) or not isinstance(results, dict):
            raise NotReadyError(_BAD_RESULTS)
        variables, rows = head.get('vars'), results.get('bindings')
        if not isinstance(variables, list) or not all(isinstance(name, str) for name in variables):
            raise NotReadyError(_BAD_RESULTS)
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise NotReadyError(_BAD_RESULTS)
        return rows

    def ask(self, query: str) -> bool:
        payload = self._query(query)
        boolean = payload.get('boolean')
        if isinstance(boolean, bool):
            return boolean
        # Some Virtuoso instances encode ASK as a single integer result binding.
        rows = self._result_rows(payload)
        value = rows[0].get('__ASK_RETVAL') if len(rows) == 1 else None
        if (not isinstance(value, dict) or value.get('type') not in ('literal', 'typed-literal')
                or value.get('datatype') != 'http://www.w3.org/2001/XMLSchema#integer'
                or value.get('value') not in ('0', '1')):
            raise NotReadyError(_BAD_RESULTS)
        return value['value'] == '1'

    def update(self, query: str) -> None:
        self._post(query, expect_json=False)
