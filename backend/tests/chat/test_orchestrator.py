import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from datetime import date

from app.assistant.outputs import Citation, GroundedAnswer
from app.chat.orchestrator import run_turn
from app.grounding.validator import ValidationResult
from app.retrieval.types import RetrievedPassage
from app.schemas.chat import TextPart, UIMessage


def _grounded_answer(chunk_id):
    return GroundedAnswer(
        answer="Revenue was $391,035 million [1].",
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="$391,035 million")],
    )


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


def _agent_run_with_registration(chunk_id):
    """Mimic a real agent run: registers the chunk it cites, then returns the answer."""

    def _run(query, deps):
        deps.registry.register(_passage(chunk_id))
        return _grounded_answer(chunk_id)

    return _run


def _sse_events(lines: list[str]) -> list[dict]:
    events = []
    for line in lines:
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):].strip()))
    return events


async def _run(user_message: UIMessage) -> list[str]:
    return [
        event
        async for event in run_turn(
            client=MagicMock(),
            thread_id=uuid4(),
            user=SimpleNamespace(id=uuid4()),
            user_message=user_message,
            thread_title="New chat",
            retriever=MagicMock(),
        )
    ]


@pytest.mark.anyio
async def test_run_turn_empty_message_streams_error_without_running_agent():
    user_message = UIMessage(role="user", parts=[TextPart(text="   ")])

    with patch("app.chat.orchestrator.run_document_agent") as mock_run:
        lines = await _run(user_message)

    mock_run.assert_not_called()
    events = _sse_events(lines)
    assert events[-1]["type"] == "error"


@pytest.mark.anyio
async def test_run_turn_retries_once_then_succeeds():
    chunk_id = uuid4()
    user_message = UIMessage(role="user", parts=[TextPart(text="What was revenue?")])

    validator_instance = MagicMock()
    validator_instance.validate = AsyncMock(
        side_effect=[
            ValidationResult(ok=False, error="not grounded"),
            ValidationResult(ok=True),
        ]
    )

    with (
        patch(
            "app.chat.orchestrator.run_document_agent",
            side_effect=_agent_run_with_registration(chunk_id),
        ) as mock_run,
        patch("app.chat.orchestrator.GroundingValidator", return_value=validator_instance),
        patch("app.chat.streaming.append_grounded_turn", new=AsyncMock()) as mock_persist,
    ):
        lines = await _run(user_message)

    assert mock_run.call_count == 2
    assert validator_instance.validate.call_count == 2
    mock_persist.assert_called_once()
    events = _sse_events(lines)
    assert any(e["type"] == "finish" for e in events)
    assert not any(e["type"] == "error" for e in events)


@pytest.mark.anyio
async def test_run_turn_fails_closed_after_max_attempts_without_persisting():
    chunk_id = uuid4()
    user_message = UIMessage(role="user", parts=[TextPart(text="What was revenue?")])

    validator_instance = MagicMock()
    validator_instance.validate = AsyncMock(
        return_value=ValidationResult(ok=False, error="never grounded")
    )

    with (
        patch(
            "app.chat.orchestrator.run_document_agent",
            return_value=_grounded_answer(chunk_id),
        ) as mock_run,
        patch("app.chat.orchestrator.GroundingValidator", return_value=validator_instance),
        patch("app.chat.streaming.append_grounded_turn", new=AsyncMock()) as mock_persist,
    ):
        lines = await _run(user_message)

    assert mock_run.call_count == 2  # MAX_VALIDATION_ATTEMPTS
    mock_persist.assert_not_called()
    events = _sse_events(lines)
    assert events[-1]["type"] == "error"


@pytest.mark.anyio
async def test_run_turn_success_streams_text_and_citation_events_and_persists():
    chunk_id = uuid4()
    user_message = UIMessage(role="user", parts=[TextPart(text="What was revenue?")])

    validator_instance = MagicMock()
    validator_instance.validate = AsyncMock(return_value=ValidationResult(ok=True))

    with (
        patch(
            "app.chat.orchestrator.run_document_agent",
            side_effect=_agent_run_with_registration(chunk_id),
        ),
        patch("app.chat.orchestrator.GroundingValidator", return_value=validator_instance),
        patch("app.chat.streaming.append_grounded_turn", new=AsyncMock()) as mock_persist,
    ):
        lines = await _run(user_message)

    events = _sse_events(lines)
    types = [e["type"] for e in events]
    assert "text-delta" in types
    assert "data-citation" in types
    assert types[-1] == "finish"
    mock_persist.assert_called_once()


@pytest.mark.anyio
async def test_run_turn_agent_exception_streams_error_without_persisting():
    user_message = UIMessage(role="user", parts=[TextPart(text="What was revenue?")])

    with (
        patch(
            "app.chat.orchestrator.run_document_agent",
            side_effect=RuntimeError("boom"),
        ),
        patch("app.chat.streaming.append_grounded_turn", new=AsyncMock()) as mock_persist,
    ):
        lines = await _run(user_message)

    events = _sse_events(lines)
    assert events[-1]["type"] == "error"
    mock_persist.assert_not_called()
