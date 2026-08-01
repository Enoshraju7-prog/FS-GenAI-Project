"""Pydantic models for chat request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
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


# ── Message models ───────────────────────────────────────────────────────────

class UIMessagePart(BaseModel):
    type: str
    text: str = ""


class UIMessageIn(BaseModel):
    """Incoming AI SDK UIMessage (v7 parts format)."""

    id: str | None = None
    role: str
    content: str | None = None   # v3-compat fallback
    parts: list[UIMessagePart] | None = None


class MessagePartOut(BaseModel):
    type: str
    text: str


class MessageOut(BaseModel):
    id: str
    role: str
    parts: list[MessagePartOut]


class ThreadDetailResponse(_CamelModel):
    id: str
    title: str
    messages: list[MessageOut]


# ── Stream request ────────────────────────────────────────────────────────────

class ChatStreamRequest(_CamelModel):
    thread_id: uuid.UUID
    messages: list[UIMessageIn]
