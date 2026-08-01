from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Computed, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.message_citations import MessageCitation
    from app.database.models.source_documents import SourceDocument


class DocumentChunk(Base, TimestampMixin):
    """One chunk of a source document, with embedding and full-text index."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    # pgvector column — filled during ingestion; HNSW index added in migration
    embedding = Column(Vector(settings.openai_embedding_dimensions), nullable=True)
    # Postgres auto-computes this from `content`; GIN index added in migration
    search_vector = Column(TSVECTOR, Computed("to_tsvector('english', content)", persisted=True))
    # JSONB metadata (page number, section heading, etc.); GIN index added in migration
    chunk_metadata = Column(JSONB, nullable=True)

    document: Mapped[SourceDocument] = relationship(back_populates="chunks")
    citations: Mapped[list[MessageCitation]] = relationship(back_populates="chunk")
