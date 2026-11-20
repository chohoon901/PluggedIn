"""Run the project's read-only SPARQL queries against Virtuoso."""

import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from functools import cache
from importlib.resources import files
from urllib.parse import urlsplit

from ca.uvic.ecs.csc501.cmn.contracts.errors import InputError, NotReadyError
from ca.uvic.ecs.csc501.cmn.contracts.semantic import AdapterCandidate, HighPowerPort, SemanticVehicle

from .client import SparqlClient


_BASE_GRAPH_PATTERN = 'GRAPH <https://github.com/chohoon901/PluggedIn/graph/> {'
_CQ2_DEFAULT_MINIMUM = 'VALUES ?minimumPowerKw { 100 }'
_CQ_HEADING = re.compile(r'^# --- (CQ[0-9]+): [^\r\n]+ ---$', re.MULTILINE)
_IRI_SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:')
_IRI_FORBIDDEN = re.compile(r'[\x00-\x20\x7f<>"{}|^`\\\ud800-\udfff]|%(?![0-9A-Fa-f]{2})')
_LITERAL = ('literal', 'typed-literal')
_URI = ('uri',)
_EVIDENCE = _LITERAL + _URI
_BAD_RESULTS = 'Semantic data returned an invalid query result.'
_UNAVAILABLE = 'Semantic data is temporarily unavailable.'

type _Row = dict[str, object]


@cache
def _query_templates() -> tuple[str, dict[str, str]]:
    try:
        source = files(__package__).joinpath('queries', 'sparql_queries.rq').read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        raise NotReadyError(_UNAVAILABLE) from exc

    header, *questions = _CQ_HEADING.split(source)
    prefixes = '\n'.join(line for line in header.splitlines() if line.startswith('PREFIX '))
    return prefixes, dict(zip(questions[::2], questions[1::2], strict=True))


def _is_absolute_iri(value: str) -> bool:
    return bool(_IRI_SCHEME.match(value)) and not _IRI_FORBIDDEN.search(value)


def _web_url(value: str | None) -> str | None:
    if value and _is_absolute_iri(value):
        try:
            url = urlsplit(value)
        except ValueError:
            return None
        if url.scheme in ('http', 'https') and url.hostname and url.username is None:
            return value
    return None


def _binding(row: _Row, name: str, kinds: tuple[str, ...] = _LITERAL) -> str:
    term = row.get(name)
    if isinstance(term, dict) and term.get('type') in kinds:
        value = term.get('value')
        if isinstance(value, str):
            return value
    raise NotReadyError(_BAD_RESULTS)


def _optional_binding(row: _Row, name: str, kinds: tuple[str, ...] = _LITERAL) -> str | None:
    return _binding(row, name, kinds) if name in row else None


def _vehicle_iri(row: _Row) -> str:
    iri = _binding(row, 'vehicle', _URI)
    if not _is_absolute_iri(iri):
        raise NotReadyError(_BAD_RESULTS)
    return iri


def _power_kw(row: _Row) -> Decimal:
    value = _binding(row, 'powerKw')
    try:
        power = Decimal(value)
    except InvalidOperation as exc:
        raise NotReadyError(_BAD_RESULTS) from exc
    if not power.is_finite():
        raise NotReadyError(_BAD_RESULTS)
    return power


class VirtuosoSemanticRepository:
    def __init__(self, endpoint: str, graph: str, *, client: SparqlClient | None = None,
                 require_ready: Callable[[], None] | None = None):
        self._client = client if client is not None else SparqlClient(endpoint)
        self._graph = graph
        self._require_ready = require_ready

    def _select(self, query: str) -> list[dict]:
        if self._require_ready is not None:
            self._require_ready()
        return self._client.select(query)

    def _graph_pattern(self) -> str:
        if not _is_absolute_iri(self._graph):
            raise NotReadyError(_UNAVAILABLE)
        return f'GRAPH <{self._graph}> {{'

    def _question(self, question: str, *, vehicle_iri: str | None = None) -> str:
        prefixes, questions = _query_templates()
        before, graph_marker, after = questions.get(question, '').partition(_BASE_GRAPH_PATTERN)
        if not prefixes or not graph_marker:
            raise NotReadyError(_UNAVAILABLE)
        graph = self._graph_pattern()
        selection = f'\n    VALUES ?vehicle {{ <{vehicle_iri}> }}' if vehicle_iri is not None else ''
        return f'{prefixes}\n{before}{graph}{selection}{after}'

    def fast_chargers(self, min_power_kw: Decimal) -> list[HighPowerPort]:
        query = self._question('CQ2')
        if _CQ2_DEFAULT_MINIMUM not in query:
            raise NotReadyError(_UNAVAILABLE)
        query = query.replace(_CQ2_DEFAULT_MINIMUM, f'VALUES ?minimumPowerKw {{ {min_power_kw:f} }}', 1)
        return [
            HighPowerPort(
                station_name=_optional_binding(row, 'stationName'),
                power_kw=_power_kw(row),
                connector_name=_binding(row, 'connectorName'),
                power_scope=_binding(row, 'powerEvidenceScope'),
                source_url=_web_url(_optional_binding(row, 'powerEvidenceSource', _EVIDENCE)),
                checked_on=_optional_binding(row, 'powerEvidenceCheckedOn'),
            )
            for row in self._select(query)
        ]

    def vehicles(self) -> list[SemanticVehicle]:
        prefixes, _ = _query_templates()
        query = f'''{prefixes}
SELECT DISTINCT ?vehicle ?model
WHERE {{
  {self._graph_pattern()}
    ?vehicle a plug:Vehicle .
    FILTER (isIRI(?vehicle))
    OPTIONAL {{ ?vehicle plug:vehicleModel ?model . }}
  }}
}}
ORDER BY ?model ?vehicle'''
        return [
            SemanticVehicle(iri=_vehicle_iri(row), model=_optional_binding(row, 'model'))
            for row in self._select(query)
        ]

    def adapter_candidates(self, vehicle_iri: str) -> list[AdapterCandidate]:
        if not _is_absolute_iri(vehicle_iri):
            raise InputError('Select a valid vehicle from the knowledge graph.')
        candidates = []
        for row in self._select(self._question('CQ4', vehicle_iri=vehicle_iri)):
            if _vehicle_iri(row) != vehicle_iri:
                raise NotReadyError(_BAD_RESULTS)
            candidates.append(AdapterCandidate(
                station_name=_optional_binding(row, 'stationName'),
                adapter_model=_binding(row, 'adapterModel'),
                port_connector=_binding(row, 'fromName'),
                vehicle_connector=_binding(row, 'toName'),
                port_current=_optional_binding(row, 'portCurrent'),
                source_url=_web_url(_optional_binding(row, 'adapterSource', _EVIDENCE)),
                adapter_current=_optional_binding(row, 'adapterCurrent'),
                station_street=_optional_binding(row, 'stationStreet'),
                station_city=_optional_binding(row, 'stationCity'),
            ))
        return candidates
