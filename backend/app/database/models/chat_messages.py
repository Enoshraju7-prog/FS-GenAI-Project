from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.models.message_role import MessageRole

if TYPE_CHECKING:
    from app.database.models.chat_threads import ChatThread
    from app.database.models.message_citations import MessageCitation


class ChatMessage(Base, TimestampMixin):
    """A single turn (user or assistant) inside a chat thread."""

    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("thread_id", "sequence", name="uq_chat_messages_thread_sequence"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_threads.id", ondelete="CASCADE"))
    role: Mapped[MessageRole]
    content: Mapped[str | None] = mapped_column(Text)
    parts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=sql_text("'[]'::jsonb"),
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    thread: Mapped[ChatThread] = relationship(back_populates="messages")
    citations: Mapped[list[MessageCitation]] = relationship(back_populates="message")
