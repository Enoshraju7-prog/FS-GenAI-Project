"""Pydantic models for chat request/response validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ── Thread models ────────────────────────────────────────────────────────────

class ThreadSummary(_CamelModel):
    id: str
    title: str
    updated_at: datetime


class ThreadsResponse(_CamelModel):
    threads: list[ThreadSummary]


class CreateThreadRequest(BaseModel):
    title: str = "New chat"


class ThreadCreated(_CamelModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


# ── Message parts (AI SDK v5 UIMessage shape) ───────────────────────────────

class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class CitationPayload(_CamelModel):
    citation_index: int
    chunk_id: uuid.UUID
    excerpt: str
    ticker: str
    company_name: str | None = None
    form: str
    filing_date: date
    page: str | None = None
    section: str | None = None


class CitationPart(BaseModel):
    type: Literal["data-citation"] = "data-citation"
    id: str | None = None
    data: CitationPayload


class StatusPayload(BaseModel):
    stage: str
    message: str


class StatusPart(BaseModel):
    type: Literal["data-status"] = "data-status"
    data: StatusPayload


# Status parts are transient run progress, never persisted and never fed back to the
# model — but the AI SDK keeps them on the assistant message it holds in memory, so a
# client replaying its history can legitimately send them. Accept and ignore.
MessagePart = Annotated[TextPart | CitationPart | StatusPart, Field(discriminator="type")]


class UIMessage(BaseModel):
    id: str | None = None
    role: Literal["user", "assistant", "system"]
    parts: list[MessagePart]


class ThreadDetailResponse(_CamelModel):
    id: str
    title: str
    messages: list[UIMessage]


# ── Source passage context ───────────────────────────────────────────────────

class ChunkContextPassage(_CamelModel):
    chunk_id: uuid.UUID
    chunk_index: int
    text: str
    is_anchor: bool


class ChunkContextResponse(_CamelModel):
    passages: list[ChunkContextPassage]


# ── Stream request ────────────────────────────────────────────────────────────

class ChatStreamRequest(_CamelModel):
    thread_id: uuid.UUID
    messages: list[UIMessage]
