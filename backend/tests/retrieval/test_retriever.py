from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import RankedChunkHit


def _fake_document(ticker="AAPL"):
    return SimpleNamespace(
        ticker=ticker,
        company_name="Apple Inc.",
        form="10-K",
        filing_date=date(2024, 11, 1),
        fiscal_year=2024,
        accession_number="0000320193-24-000123",
    )


def _fake_chunk(chunk_id, *, chunk_index=0, document=None):
    return SimpleNamespace(
        id=chunk_id,
        document_id=uuid4(),
        chunk_index=chunk_index,
        text=f"chunk text {chunk_index}",
        page="12",
        section="Item 7",
        document=document or _fake_document(),
    )


@contextmanager
def _fake_get_session():
    yield MagicMock()


def test_search_preserves_fusion_order_on_hydration():
    hit_a, hit_b = uuid4(), uuid4()
    chunk_a = _fake_chunk(hit_a, chunk_index=5)
    chunk_b = _fake_chunk(hit_b, chunk_index=10)

    with (
        patch("app.retrieval.retriever.get_session", _fake_get_session),
        patch("app.retrieval.retriever.embed_query", return_value=[0.1]),
        patch(
            "app.retrieval.retriever.semantic_search",
            return_value=[
                RankedChunkHit(chunk_id=hit_b, rank=1, score=0.9),
                RankedChunkHit(chunk_id=hit_a, rank=2, score=0.4),
            ],
        ),
        patch("app.retrieval.retriever.full_text_search", return_value=[]),
        patch(
            "app.retrieval.retriever.get_chunks_by_ids",
            return_value={hit_a: chunk_a, hit_b: chunk_b},
        ),
        patch("app.retrieval.retriever.get_surrounding_chunks", return_value=[]),
    ):
        passages = DocumentRetriever().search("query", include_neighbors=False)

    # hit_b outranks hit_a in the semantic leg (only signal here), so fusion -> hydration
    # must preserve that order rather than e.g. falling back to dict/hash order.
    assert [p.chunk_id for p in passages] == [hit_b, hit_a]
    assert all(p.neighbors == [] for p in passages)


def test_search_attaches_neighbors_with_zero_fusion_score():
    hit_id = uuid4()
    neighbor_before, neighbor_after = uuid4(), uuid4()
    chunk = _fake_chunk(hit_id, chunk_index=5)

    with (
        patch("app.retrieval.retriever.get_session", _fake_get_session),
        patch("app.retrieval.retriever.embed_query", return_value=[0.1]),
        patch(
            "app.retrieval.retriever.semantic_search",
            return_value=[RankedChunkHit(chunk_id=hit_id, rank=1, score=0.9)],
        ),
        patch("app.retrieval.retriever.full_text_search", return_value=[]),
        patch(
            "app.retrieval.retriever.get_chunks_by_ids",
            return_value={hit_id: chunk},
        ),
        patch(
            "app.retrieval.retriever.get_surrounding_chunks",
            return_value=[
                _fake_chunk(neighbor_before, chunk_index=4),
                _fake_chunk(neighbor_after, chunk_index=6),
            ],
        ),
    ):
        passages = DocumentRetriever().search("query", include_neighbors=True)

    assert len(passages) == 1
    neighbor_ids = {n.chunk_id for n in passages[0].neighbors}
    assert neighbor_ids == {neighbor_before, neighbor_after}
    assert all(n.fusion_score == 0.0 for n in passages[0].neighbors)


def test_search_deduplicates_neighbor_already_present_in_fused_hits():
    hit_a, hit_b = uuid4(), uuid4()
    chunk_a = _fake_chunk(hit_a, chunk_index=5)
    chunk_b = _fake_chunk(hit_b, chunk_index=6)

    def surrounding_side_effect(session, chunk_id, radius):
        # hit_a's neighbor list includes hit_b, which is also a top-level fused hit
        if chunk_id == hit_a:
            return [chunk_b]
        return []

    with (
        patch("app.retrieval.retriever.get_session", _fake_get_session),
        patch("app.retrieval.retriever.embed_query", return_value=[0.1]),
        patch(
            "app.retrieval.retriever.semantic_search",
            return_value=[
                RankedChunkHit(chunk_id=hit_a, rank=1, score=0.9),
                RankedChunkHit(chunk_id=hit_b, rank=2, score=0.8),
            ],
        ),
        patch("app.retrieval.retriever.full_text_search", return_value=[]),
        patch(
            "app.retrieval.retriever.get_chunks_by_ids",
            return_value={hit_a: chunk_a, hit_b: chunk_b},
        ),
        patch(
            "app.retrieval.retriever.get_surrounding_chunks",
            side_effect=surrounding_side_effect,
        ),
    ):
        passages = DocumentRetriever().search("query", include_neighbors=True)

    hit_a_passage = next(p for p in passages if p.chunk_id == hit_a)
    assert hit_a_passage.neighbors == []


def test_search_returns_empty_list_when_no_hits():
    with (
        patch("app.retrieval.retriever.get_session", _fake_get_session),
        patch("app.retrieval.retriever.embed_query", return_value=[0.1]),
        patch("app.retrieval.retriever.semantic_search", return_value=[]),
        patch("app.retrieval.retriever.full_text_search", return_value=[]),
    ):
        passages = DocumentRetriever().search("query")

    assert passages == []
