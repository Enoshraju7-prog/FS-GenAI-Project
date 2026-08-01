from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.models.message_role import MessageRole

if TYPE_CHECKING:
    from app.database.models.chat_threads import ChatThread
    from app.database.models.message_citations import MessageCitation


class ChatMessage(Base, TimestampMixin):
    """A single turn (user or assistant) inside a chat thread."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_threads.id", ondelete="CASCADE"))
    role: Mapped[MessageRole]
    content: Mapped[str] = mapped_column(Text)

    thread: Mapped[ChatThread] = relationship(back_populates="messages")
    citations: Mapped[list[MessageCitation]] = relationship(back_populates="message")
