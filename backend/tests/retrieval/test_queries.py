from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.retrieval.queries import _build_filters, full_text_search, semantic_search
from app.retrieval.types import SearchFilters


def test_build_filters_returns_empty_clause_when_no_filters():
    clause = _build_filters(None)

    assert clause.sql == ""
    assert clause.params == {}


def test_build_filters_combines_ticker_fiscal_years_and_form():
    clause = _build_filters(
        SearchFilters(ticker="AAPL", fiscal_years=[2023, 2024], form="10-K")
    )

    assert "sd.ticker = :ticker" in clause.sql
    assert "sd.fiscal_year = ANY(:fiscal_years)" in clause.sql
    assert "sd.form = :form" in clause.sql
    assert clause.params == {
        "ticker": "AAPL",
        "fiscal_years": [2023, 2024],
        "form": "10-K",
    }


def test_build_filters_omits_unset_fields():
    clause = _build_filters(SearchFilters(ticker="AAPL"))

    assert clause.params == {"ticker": "AAPL"}
    assert "fiscal_year" not in clause.sql
    assert "form" not in clause.sql


def _mock_session_returning(rows):
    session = MagicMock()
    session.execute.return_value.all.return_value = rows
    return session


def test_semantic_search_maps_rows_to_ranked_hits_in_order():
    id_a, id_b = uuid4(), uuid4()
    rows = [
        SimpleNamespace(id=id_a, score=0.9),
        SimpleNamespace(id=id_b, score=0.5),
    ]
    session = _mock_session_returning(rows)

    hits = semantic_search(session, [0.1, 0.2], limit=10)

    assert [h.chunk_id for h in hits] == [id_a, id_b]
    assert [h.rank for h in hits] == [1, 2]
    assert [h.score for h in hits] == [0.9, 0.5]

    params = session.execute.call_args.args[1]
    assert params["limit"] == 10
    assert params["query_vec"] == "[0.1,0.2]"


def test_semantic_search_applies_filters_to_bound_params():
    session = _mock_session_returning([])

    semantic_search(
        session,
        [0.1],
        limit=5,
        filters=SearchFilters(ticker="MSFT"),
    )

    sql_text = str(session.execute.call_args.args[0])
    params = session.execute.call_args.args[1]
    assert "sd.ticker = :ticker" in sql_text
    assert params["ticker"] == "MSFT"


def test_full_text_search_maps_rows_to_ranked_hits():
    chunk_id = uuid4()
    rows = [SimpleNamespace(id=chunk_id, score=0.42)]
    session = _mock_session_returning(rows)

    hits = full_text_search(session, "revenue mix", limit=10)

    assert len(hits) == 1
    assert hits[0].chunk_id == chunk_id
    assert hits[0].rank == 1
    assert hits[0].score == 0.42
    params = session.execute.call_args.args[1]
    assert params["query_text"] == "revenue mix"


def test_full_text_search_score_none_when_row_score_is_none():
    chunk_id = uuid4()
    rows = [SimpleNamespace(id=chunk_id, score=None)]
    session = _mock_session_returning(rows)

    hits = full_text_search(session, "anything", limit=10)

    assert hits[0].score is None
