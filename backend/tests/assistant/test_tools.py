from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.assistant import tools
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.retrieval.types import RetrievedPassage, SearchFilters


def _passage(chunk_id) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        document_id=uuid4(),
        chunk_index=0,
        text="Total net sales were $391,035 million.",
        page="35",
        section="Item 7",
        fusion_score=1.0,
        ticker="AAPL",
        company_name="Apple Inc.",
        form="10-K",
        filing_date=date(2024, 11, 1),
        fiscal_year=2024,
        accession_number="acc-1",
        neighbors=[],
    )


def _fake_chunk(chunk_id, *, chunk_index=0, document=None):
    return SimpleNamespace(
        id=chunk_id,
        document_id=uuid4(),
        chunk_index=chunk_index,
        text="some text",
        page="1",
        section=None,
        document=document
        or SimpleNamespace(
            ticker="AAPL",
            company_name="Apple Inc.",
            form="10-K",
            filing_date=date(2024, 11, 1),
            fiscal_year=2024,
            accession_number="acc-1",
        ),
    )


def _ctx(deps: DocumentAgentDeps):
    return SimpleNamespace(deps=deps)


def _deps() -> DocumentAgentDeps:
    return DocumentAgentDeps(
        retriever=MagicMock(),
        registry=TurnRegistry(),
        thread_id=uuid4(),
        user_id=uuid4(),
    )


@contextmanager
def _fake_get_session():
    yield MagicMock()


@pytest.mark.anyio
async def test_search_filings_parses_filters_and_registers_passages():
    chunk_id = uuid4()
    deps = _deps()
    deps.retriever.search.return_value = [_passage(chunk_id)]

    result = await tools.search_filings(
        _ctx(deps), "revenue mix", ticker="AAPL", form="10-K", fiscal_years="2023,2024"
    )

    called_filters: SearchFilters = deps.retriever.search.call_args.kwargs["filters"]
    assert called_filters.ticker == "AAPL"
    assert called_filters.form == "10-K"
    assert called_filters.fiscal_years == [2023, 2024]
    assert chunk_id in deps.registry.passages_by_chunk_id
    assert "391,035" in result


@pytest.mark.anyio
async def test_search_filings_no_filters_passed_through():
    deps = _deps()
    deps.retriever.search.return_value = []

    await tools.search_filings(_ctx(deps), "revenue mix")

    called_filters: SearchFilters = deps.retriever.search.call_args.kwargs["filters"]
    assert called_filters.ticker is None
    assert called_filters.form is None
    assert called_filters.fiscal_years is None


@pytest.mark.anyio
async def test_read_chunk_invalid_uuid_returns_error_string():
    deps = _deps()

    result = await tools.read_chunk(_ctx(deps), "not-a-uuid")

    assert result.startswith("Error:")
    assert deps.registry.passages_by_chunk_id == {}


@pytest.mark.anyio
async def test_read_chunk_not_found_returns_error_string():
    deps = _deps()
    with (
        patch("app.assistant.tools.get_session", _fake_get_session),
        patch("app.assistant.tools.get_chunk_with_document", return_value=None),
    ):
        result = await tools.read_chunk(_ctx(deps), str(uuid4()))

    assert "not found" in result


@pytest.mark.anyio
async def test_read_chunk_found_registers_passage():
    chunk_id = uuid4()
    chunk = _fake_chunk(chunk_id)
    with (
        patch("app.assistant.tools.get_session", _fake_get_session),
        patch(
            "app.assistant.tools.get_chunk_with_document",
            return_value=(chunk, chunk.document),
        ),
    ):
        deps = _deps()
        result = await tools.read_chunk(_ctx(deps), str(chunk_id))

    assert chunk_id in deps.registry.passages_by_chunk_id
    assert "some text" in result


@pytest.mark.anyio
async def test_read_chunks_invalid_uuid_returns_error_string():
    deps = _deps()

    result = await tools.read_chunks(_ctx(deps), ["not-a-uuid"])

    assert result.startswith("Error:")


@pytest.mark.anyio
async def test_read_chunks_empty_list_returns_error_string():
    deps = _deps()

    result = await tools.read_chunks(_ctx(deps), [])

    assert "at least one UUID" in result


@pytest.mark.anyio
async def test_read_chunks_registers_all_found_passages():
    id_a, id_b = uuid4(), uuid4()
    chunks_by_id = {id_a: _fake_chunk(id_a), id_b: _fake_chunk(id_b)}
    with (
        patch("app.assistant.tools.get_session", _fake_get_session),
        patch("app.assistant.tools.get_chunks_by_ids", return_value=chunks_by_id),
    ):
        deps = _deps()
        result = await tools.read_chunks(_ctx(deps), [str(id_a), str(id_b)])

    assert set(deps.registry.passages_by_chunk_id) == {id_a, id_b}
    assert "not found" not in result


@pytest.mark.anyio
async def test_read_surrounding_chunks_invalid_radius_returns_error():
    deps = _deps()

    result = await tools.read_surrounding_chunks(_ctx(deps), str(uuid4()), radius=0)

    assert "radius must be 1 or greater" in result


@pytest.mark.anyio
async def test_read_surrounding_chunks_anchor_not_found_returns_error():
    deps = _deps()
    with (
        patch("app.assistant.tools.get_session", _fake_get_session),
        patch("app.assistant.tools.get_chunk_with_document", return_value=None),
    ):
        result = await tools.read_surrounding_chunks(_ctx(deps), str(uuid4()))

    assert "not found" in result


@pytest.mark.anyio
async def test_read_surrounding_chunks_registers_anchor_and_neighbors():
    anchor_id, neighbor_id = uuid4(), uuid4()
    anchor = _fake_chunk(anchor_id)
    neighbor = _fake_chunk(neighbor_id)
    with (
        patch("app.assistant.tools.get_session", _fake_get_session),
        patch(
            "app.assistant.tools.get_chunk_with_document",
            return_value=(anchor, anchor.document),
        ),
        patch("app.assistant.tools.get_surrounding_chunks", return_value=[neighbor]),
    ):
        deps = _deps()
        result = await tools.read_surrounding_chunks(_ctx(deps), str(anchor_id))

    assert set(deps.registry.passages_by_chunk_id) == {anchor_id, neighbor_id}
    assert "not found" not in result
