"""Read and update the private application graph in Virtuoso."""

from dataclasses import dataclass
from hashlib import sha256
from itertools import batched
from threading import Lock
from uuid import uuid4

from ...cmn.contracts.errors import ConflictError, NotReadyError
from .client import SparqlClient
from .rdf import MIGRATION, Term, Triple, iri_ref, sparql_triples


_STATE = MIGRATION + 'applicationStore'
_REVISION = MIGRATION + 'revision'
_RECEIPT = MIGRATION + 'committedRevision'
_DATASET = MIGRATION + 'dataset'
_BOOTSTRAP = (_STATE, MIGRATION + 'bootstrap', Term('1'))
_PENDING = (_STATE, MIGRATION + 'importPending', Term('1'))
_IMPORT_SOURCE = MIGRATION + 'importSource'
_IMPORT_BATCH_SIZE = 200
_NOT_INITIALIZED = 'Initialize the private Virtuoso application graph first.'
_INVALID_GRAPH = 'The Virtuoso application graph is incomplete or invalid.'
_STALE = 'The charging data changed while you were editing. Please try again.'


@dataclass(frozen=True, slots=True)
class GraphState:
    # 같은 데이터 판본인지 확인하기 위해 Virtuoso에 저장한 변경 식별자입니다.
    revision: Term
    # 한 번의 읽기에서 가져온 애플리케이션 그래프의 트리플입니다.
    triples: frozenset[Triple]


def _triple(row: dict) -> Triple:
    subject, predicate, obj = (Term.from_binding(row[name]) for name in ('subject', 'predicate', 'object'))
    if subject.kind != 'uri' or predicate.kind != 'uri':
        raise ValueError('Expected named subjects and predicates.')
    return subject.value, predicate.value, obj


class VirtuosoStore:
    def __init__(self, client: SparqlClient, graph: str, dataset: str):
        self.client, self.graph, self.dataset = client, graph, dataset
        self._graph_ref = iri_ref(graph)
        self._writes = Lock()
        self._loaded: GraphState | None = None

    @classmethod
    def from_settings(cls, settings):
        return cls(
            SparqlClient(settings.app_sparql_endpoint, username=settings.virtuoso_user,
                         password=settings.virtuoso_password, require_authentication=True,
                         timeout_seconds=12.0),
            settings.app_sparql_graph, settings.rdf_dataset,
        )

    def _pattern(self, pattern: str) -> str:
        return f'GRAPH {self._graph_ref} {{ {pattern} }}'

    def _has(self, triple: Triple) -> bool:
        return self.client.ask(f'ASK {{ {self._pattern(sparql_triples({triple}))} }}')

    def load(self, *, allow_pending: bool = False) -> GraphState:
        cached = self._loaded
        if not allow_pending and cached is not None and self._has((_STATE, _REVISION, cached.revision)):
            return cached
        pattern = self._pattern(f'?subject ?predicate ?object . FILTER (?predicate != {iri_ref(_RECEIPT)})')
        rows = self.client.select(
            'SELECT ?subject ?predicate ?object ?total WHERE {'
            f' {{ SELECT (COUNT(*) AS ?total) WHERE {{ {pattern} }} }}'
            f' {pattern} }}'
        )
        if not rows:
            raise NotReadyError(_NOT_INITIALIZED)
        try:
            triples = frozenset(_triple(row) for row in rows)
            total = int(Term.from_binding(rows[0]['total']).value)
            revisions = [obj for subject, predicate, obj in triples if (subject, predicate) == (_STATE, _REVISION)]
            datasets = [obj.value for subject, predicate, obj in triples if (subject, predicate) == (_STATE, _DATASET)]
            if datasets != [self.dataset] or len(triples) != total or len(revisions) != 1:
                raise ValueError('Snapshot is inconsistent.')
            if revisions[0].kind != 'literal':
                raise ValueError('Invalid revision.')
        except (KeyError, TypeError, ValueError) as exc:
            raise NotReadyError(_INVALID_GRAPH) from exc
        if any((subject, predicate) == _PENDING[:2] for subject, predicate, _ in triples) and not allow_pending:
            raise NotReadyError('Finish importing the Virtuoso application graph first.')
        state = GraphState(revisions[0], triples)
        if not allow_pending:
            self._loaded = state
        return state

    def health(self) -> bool:
        try:
            self.load()
        except NotReadyError:
            return False
        return True

    def require_ready(self) -> None:
        pattern = self._pattern(
            f'{iri_ref(_STATE)} {iri_ref(_REVISION)} ?revision ; '
            f'{iri_ref(_DATASET)} {Term(self.dataset).sparql()} . '
            f'FILTER NOT EXISTS {{ {iri_ref(_STATE)} {iri_ref(_PENDING[1])} ?pending }}'
        )
        if not self.client.ask(f'ASK {{ {pattern} }}'):
            raise NotReadyError(_NOT_INITIALIZED)

    def commit(self, state: GraphState, removed: set[Triple], added: set[Triple]) -> GraphState:
        previous = (_STATE, _REVISION, state.revision)
        token = Term(uuid4().hex)
        revision = (_STATE, _REVISION, token)
        receipt = (_STATE, _RECEIPT, token)
        removed = removed | {previous}
        added = added | {revision}
        delete = sparql_triples(removed)
        insert = sparql_triples(added | {receipt})
        expected = sparql_triples({previous})
        with self._writes:
            self._update(
                f'WITH {self._graph_ref} DELETE {{ {delete} }} INSERT {{ {insert} }} WHERE {{ {expected} }}',
                receipt,
            )
        return GraphState(token, (state.triples - removed) | added)

    def _update(self, query: str, confirmation: Triple) -> None:
        try:
            self.client.update(query)
        except NotReadyError:
            # A timeout may occur after Virtuoso commits. Check before reporting failure.
            if not self._has(confirmation):
                raise
            return
        if not self._has(confirmation):
            raise ConflictError(_STALE)

    def _require_private(self, anonymous: SparqlClient, marker: str) -> None:
        # Verify the graph is hidden from the same unauthenticated endpoint used for public queries.
        if (anonymous.ask(f'ASK {{ {self._pattern(marker)} }}')
                or anonymous.ask(f'ASK FROM {self._graph_ref} {{ {marker} }}')):
            raise NotReadyError('Require authentication for the application graph before importing profiles.')

    def initialize(self, triples: set[Triple], anonymous: SparqlClient) -> None:
        """Populate an empty, private graph, or resume an unfinished import."""
        marker = sparql_triples({_BOOTSTRAP})
        graph_marker = self._pattern(marker)
        fingerprint = sha256(sparql_triples(triples).encode('utf-8')).hexdigest()
        source = (_STATE, _IMPORT_SOURCE, Term(fingerprint))
        existing = self._pattern('?subject ?predicate ?object .')
        with self._writes:
            if self._has(_PENDING):
                self._require_private(anonymous, sparql_triples({_PENDING}))
            else:
                if not self._has(_BOOTSTRAP):
                    self.client.update(f'INSERT {{ {graph_marker} }} WHERE {{ FILTER NOT EXISTS {{ {existing} }} }}')
                if not self._has(_BOOTSTRAP):
                    raise ConflictError('The Virtuoso application graph already contains data.')

                self._require_private(anonymous, marker)
                revision = (_STATE, _REVISION, Term(uuid4().hex))
                metadata = {_PENDING, source, revision, (_STATE, _DATASET, Term(self.dataset))}
                insert = self._pattern(sparql_triples(metadata))
                extra = self._pattern(
                    '?subject ?predicate ?object . '
                    f'FILTER (!(?subject = {iri_ref(_BOOTSTRAP[0])} && ?predicate = {iri_ref(_BOOTSTRAP[1])}'
                    f' && ?object = {_BOOTSTRAP[2].sparql()}))'
                )
                self._update(f'INSERT {{ {insert} }} WHERE {{ {graph_marker}'
                             f' FILTER NOT EXISTS {{ {extra} }} }}', revision)

            if not self._has(source):
                raise ConflictError('Resume the import with the same SQLite snapshot and metadata.')
            pending_source = self._pattern(sparql_triples({_PENDING, source}))
            ordered = sorted(triples, key=lambda triple: (triple[0], triple[1], triple[2].sparql()))
            for batch in batched(ordered, _IMPORT_BATCH_SIZE):
                insert = self._pattern(sparql_triples(batch))
                self.client.update(f'INSERT {{ {insert} }} WHERE {{ {pending_source} }}')

    def finish_import(self, state: GraphState) -> None:
        marker = {triple for triple in state.triples if triple[:2] == _PENDING[:2]}
        if not marker:
            raise ConflictError('The Virtuoso application graph is already ready.')
        import_metadata = {triple for triple in state.triples
                           if triple[0] == _STATE and triple[1] in (_IMPORT_SOURCE, _BOOTSTRAP[1])}
        self.commit(state, marker | import_metadata, set())
