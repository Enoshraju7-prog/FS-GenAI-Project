from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import Citation, GroundedAnswer
from app.chat.messages import (
    DEFAULT_THREAD_TITLE,
    build_assistant_message,
    citation_parts_from_grounded_answer,
    extract_last_user_message,
    row_to_ui_message,
    text_from_parts,
    title_from_user_message,
    ui_message_to_insert,
)
from app.retrieval.types import RetrievedPassage
from app.schemas.chat import CitationPart, TextPart, UIMessage


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


def test_text_from_parts_joins_only_text_parts():
    chunk_id = uuid4()
    parts = [
        TextPart(text="Hello "),
        CitationPart(
            data={
                "citationIndex": 1,
                "chunkId": chunk_id,
                "excerpt": "x",
                "ticker": "AAPL",
                "form": "10-K",
                "filingDate": "2024-11-01",
            }
        ),
        TextPart(text="world"),
    ]
    assert text_from_parts(parts) == "Hello world"


def test_extract_last_user_message_returns_most_recent_user_message():
    messages = [
        UIMessage(role="user", parts=[TextPart(text="first")]),
        UIMessage(role="assistant", parts=[TextPart(text="reply")]),
        UIMessage(role="user", parts=[TextPart(text="second")]),
    ]
    result = extract_last_user_message(messages)
    assert text_from_parts(result.parts) == "second"


def test_extract_last_user_message_raises_422_when_no_user_message():
    with pytest.raises(HTTPException) as exc_info:
        extract_last_user_message([UIMessage(role="assistant", parts=[TextPart(text="hi")])])
    assert exc_info.value.status_code == 422


def test_ui_message_to_insert_serializes_parts_and_content():
    message = UIMessage(role="user", parts=[TextPart(text="hello")])
    thread_id = uuid4()

    row = ui_message_to_insert(message, thread_id=thread_id, sequence=3)

    assert row["thread_id"] == str(thread_id)
    assert row["role"] == "user"
    assert row["content"] == "hello"
    assert row["sequence"] == 3
    assert row["parts"] == [{"type": "text", "text": "hello"}]


def test_ui_message_to_insert_content_none_when_no_text():
    chunk_id = uuid4()
    message = UIMessage(
        id=str(uuid4()),
        role="assistant",
        parts=[
            CitationPart(
                data={
                    "citationIndex": 1,
                    "chunkId": chunk_id,
                    "excerpt": "x",
                    "ticker": "AAPL",
                    "form": "10-K",
                    "filingDate": "2024-11-01",
                }
            )
        ],
    )
    row = ui_message_to_insert(message, thread_id=uuid4(), sequence=0)
    assert row["content"] is None


def test_row_to_ui_message_parses_parts():
    message_id = uuid4()
    row = {
        "id": str(message_id),
        "role": "user",
        "content": "hello",
        "parts": [{"type": "text", "text": "hello"}],
    }
    message = row_to_ui_message(row)
    assert message.id == str(message_id)
    assert text_from_parts(message.parts) == "hello"


def test_row_to_ui_message_falls_back_to_content_when_parts_empty():
    row = {"id": str(uuid4()), "role": "assistant", "content": "legacy reply", "parts": []}
    message = row_to_ui_message(row)
    assert len(message.parts) == 1
    assert text_from_parts(message.parts) == "legacy reply"


def test_citation_parts_from_grounded_answer_looks_up_registry():
    chunk_id = uuid4()
    registry = TurnRegistry()
    registry.register(_passage(chunk_id))
    answer = GroundedAnswer(
        answer="Revenue was $391,035 million [1].",
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="$391,035 million")],
    )

    parts = citation_parts_from_grounded_answer(answer, registry)

    assert len(parts) == 1
    assert parts[0].data.chunk_id == chunk_id
    assert parts[0].data.ticker == "AAPL"
    assert parts[0].data.page == "35"


def test_build_assistant_message_includes_text_and_citations():
    chunk_id = uuid4()
    registry = TurnRegistry()
    registry.register(_passage(chunk_id))
    answer = GroundedAnswer(
        answer="Revenue was $391,035 million [1].",
        citations=[Citation(citation_index=1, chunk_id=chunk_id, excerpt="$391,035 million")],
    )

    message = build_assistant_message(answer, registry)

    assert message.role == "assistant"
    assert isinstance(message.parts[0], TextPart)
    assert isinstance(message.parts[1], CitationPart)


def test_title_from_user_message_truncates_long_text():
    long_text = "x" * 300
    message = UIMessage(role="user", parts=[TextPart(text=long_text)])
    title = title_from_user_message(message)
    assert len(title) == 255
    assert title.endswith("...")


def test_title_from_user_message_defaults_when_empty():
    message = UIMessage(role="user", parts=[TextPart(text="   ")])
    assert title_from_user_message(message) == DEFAULT_THREAD_TITLE
