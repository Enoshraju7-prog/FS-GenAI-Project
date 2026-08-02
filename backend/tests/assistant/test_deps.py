from datetime import date
from uuid import uuid4

from app.assistant.deps import TurnRegistry
from app.retrieval.types import RetrievedPassage


def _passage(chunk_id, *, neighbors=None) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        document_id=uuid4(),
        chunk_index=0,
        text="some text",
        page="1",
        section=None,
        fusion_score=1.0,
        ticker="AAPL",
        company_name="Apple Inc.",
        form="10-K",
        filing_date=date(2024, 1, 1),
        fiscal_year=2024,
        accession_number="acc-1",
        neighbors=neighbors or [],
    )


def test_register_adds_passage_by_chunk_id():
    chunk_id = uuid4()
    registry = TurnRegistry()

    registry.register(_passage(chunk_id))

    assert chunk_id in registry.passages_by_chunk_id


def test_register_also_registers_neighbors():
    chunk_id, neighbor_id = uuid4(), uuid4()
    neighbor = _passage(neighbor_id)
    registry = TurnRegistry()

    registry.register(_passage(chunk_id, neighbors=[neighbor]))

    assert chunk_id in registry.passages_by_chunk_id
    assert neighbor_id in registry.passages_by_chunk_id


def test_register_same_chunk_id_overwrites_not_duplicates():
    chunk_id = uuid4()
    registry = TurnRegistry()

    registry.register(_passage(chunk_id))
    registry.register(_passage(chunk_id))

    assert len(registry.passages_by_chunk_id) == 1


def test_register_many_registers_every_passage():
    ids = [uuid4() for _ in range(3)]
    registry = TurnRegistry()

    registry.register_many([_passage(i) for i in ids])

    assert set(registry.passages_by_chunk_id) == set(ids)
