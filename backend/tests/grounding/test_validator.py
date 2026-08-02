from datetime import date
from uuid import uuid4

import pytest

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import (
    CitationGroundingCase,
    CitationGroundingDecision,
    GroundingValidator,
)
from app.retrieval.types import RetrievedPassage


def _passage(chunk_id, text="Total net sales were $391,035 million.") -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        document_id=uuid4(),
        chunk_index=0,
        text=text,
        page="35",
        section="Item 7",
        fusion_score=1.0,
        ticker="AAPL",
        company_name="Apple Inc.",
        form="10-K",
        filing_date=date(2024, 11, 1),
        fiscal_year=2024,
        accession_number="0000320193-24-000123",
        neighbors=[],
    )


class _SupportedJudge:
    async def judge(self, cases: list[CitationGroundingCase]) -> list[CitationGroundingDecision]:
        return [
            CitationGroundingDecision(citation_index=case.citation_index, supported=True, reason="ok")
            for case in cases
        ]


class _UnsupportedJudge:
    async def judge(self, cases: list[CitationGroundingCase]) -> list[CitationGroundingDecision]:
        return [
            CitationGroundingDecision(
                citation_index=case.citation_index, supported=False, reason="not in source"
            )
            for case in cases
        ]


class _ExplodingJudge:
    async def judge(self, cases: list[CitationGroundingCase]) -> list[CitationGroundingDecision]:
        raise RuntimeError("OpenAI API down")


@pytest.mark.anyio
async def test_empty_answer_fails():
    result = await GroundingValidator().validate(GroundedAnswer(answer="  "), TurnRegistry())
    assert not result.ok


@pytest.mark.anyio
async def test_insufficient_evidence_with_citations_fails():
    chunk_id = uuid4()
    answer = GroundedAnswer(
        answer="Not enough evidence.",
        insufficient_evidence=True,
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="x")],
    )
    result = await GroundingValidator().validate(answer, TurnRegistry())
    assert not result.ok


@pytest.mark.anyio
async def test_insufficient_evidence_with_no_citations_passes_without_judge():
    answer = GroundedAnswer(answer="Not enough evidence.", insufficient_evidence=True)
    result = await GroundingValidator(judge=_ExplodingJudge()).validate(answer, TurnRegistry())
    assert result.ok


@pytest.mark.anyio
async def test_grounded_answer_with_no_citations_fails():
    answer = GroundedAnswer(answer="Revenue was $391 billion [1].")
    result = await GroundingValidator().validate(answer, TurnRegistry())
    assert not result.ok


@pytest.mark.anyio
async def test_citations_present_but_empty_registry_fails():
    chunk_id = uuid4()
    answer = GroundedAnswer(
        answer="Revenue was $391 billion [1].",
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="x")],
    )
    result = await GroundingValidator().validate(answer, TurnRegistry())
    assert not result.ok


@pytest.mark.anyio
async def test_duplicate_citation_index_fails():
    chunk_id = uuid4()
    registry = TurnRegistry()
    registry.register(_passage(chunk_id))
    answer = GroundedAnswer(
        answer="Revenue was $391 billion [1][1].",
        citations=[
            Citation(citation_index=1, chunk_id=chunk_id, excerpt="x"),
            Citation(citation_index=1, chunk_id=chunk_id, excerpt="y"),
        ],
    )
    result = await GroundingValidator().validate(answer, registry)
    assert not result.ok


@pytest.mark.anyio
async def test_non_contiguous_indices_fail():
    chunk_id = uuid4()
    registry = TurnRegistry()
    registry.register(_passage(chunk_id))
    answer = GroundedAnswer(
        answer="Revenue was $391 billion [2].",
        citations=[Citation(citation_index=2, chunk_id=chunk_id, excerpt="x")],
    )
    result = await GroundingValidator().validate(answer, registry)
    assert not result.ok


@pytest.mark.anyio
async def test_markers_not_matching_citations_fail():
    chunk_id = uuid4()
    registry = TurnRegistry()
    registry.register(_passage(chunk_id))
    answer = GroundedAnswer(
        answer="Revenue was $391 billion, no marker here.",
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="x")],
    )
    result = await GroundingValidator().validate(answer, registry)
    assert not result.ok


@pytest.mark.anyio
async def test_citation_to_unregistered_chunk_fails():
    registered_id, unregistered_id = uuid4(), uuid4()
    registry = TurnRegistry()
    registry.register(_passage(registered_id))
    answer = GroundedAnswer(
        answer="Revenue was $391 billion [1].",
        citations=[Citation(citation_index=1, chunk_id=unregistered_id, excerpt="x")],
    )
    result = await GroundingValidator().validate(answer, registry)
    assert not result.ok
    assert str(unregistered_id) in result.error


@pytest.mark.anyio
async def test_supported_judge_decision_passes():
    chunk_id = uuid4()
    registry = TurnRegistry()
    registry.register(_passage(chunk_id))
    answer = GroundedAnswer(
        answer="Revenue was $391,035 million [1].",
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="$391,035 million")],
    )
    result = await GroundingValidator(judge=_SupportedJudge()).validate(answer, registry)
    assert result.ok


@pytest.mark.anyio
async def test_unsupported_judge_decision_fails_with_reason():
    chunk_id = uuid4()
    registry = TurnRegistry()
    registry.register(_passage(chunk_id))
    answer = GroundedAnswer(
        answer="Revenue was $999 billion [1].",
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="$999 billion")],
    )
    result = await GroundingValidator(judge=_UnsupportedJudge()).validate(answer, registry)
    assert not result.ok
    assert "not in source" in result.error


@pytest.mark.anyio
async def test_judge_exception_fails_closed():
    chunk_id = uuid4()
    registry = TurnRegistry()
    registry.register(_passage(chunk_id))
    answer = GroundedAnswer(
        answer="Revenue was $391,035 million [1].",
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="$391,035 million")],
    )
    result = await GroundingValidator(judge=_ExplodingJudge()).validate(answer, registry)
    assert not result.ok
    assert "OpenAI API down" in result.error
