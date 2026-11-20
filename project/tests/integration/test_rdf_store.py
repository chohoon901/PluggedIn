from collections import deque

import pytest

from ca.uvic.ecs.csc501.cmn.contracts.errors import ConflictError, NotReadyError
from ca.uvic.ecs.csc501.dal.semantic.rdf import Term
from ca.uvic.ecs.csc501.dal.semantic.store import GraphState, VirtuosoStore


class ScriptedSparql:
    def __init__(self, answers):
        self.answers = deque(answers)
        self.updates = []

    def ask(self, query):
        return self.answers.popleft()

    def update(self, query):
        self.updates.append(query)


def test_import_refuses_to_send_profiles_to_an_anonymously_readable_graph():
    private = ScriptedSparql([False, False, True])
    public = ScriptedSparql([True])
    store = VirtuosoStore(private, 'https://example.test/graph', 'sample20')
    profile = ('https://example.test/profile', 'https://example.test/name', Term('Private profile'))

    with pytest.raises(NotReadyError, match='Require authentication'):
        store.initialize({profile}, public)

    assert len(private.updates) == 1
    assert 'Private profile' not in private.updates[0]


def test_update_requires_the_previous_graph_revision_in_the_same_statement():
    client = ScriptedSparql([False])
    store = VirtuosoStore(client, 'https://example.test/graph', 'sample20')
    old = ('https://example.test/profile', 'https://example.test/name', Term('Old name'))
    new = (old[0], old[1], Term('Edited name'))

    with pytest.raises(ConflictError):
        store.commit(GraphState(Term('older revision'), frozenset({old})), {old}, {new})

    update, = client.updates
    deletion, rest = update.split('INSERT', 1)
    insertion, precondition = rest.split('WHERE', 1)
    assert 'Old name' in deletion
    assert 'Edited name' in insertion
    assert 'older revision' in precondition
