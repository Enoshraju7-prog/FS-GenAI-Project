from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.document_chunks import DocumentChunk
    from app.database.models.users import User


class SourceDocument(Base, TimestampMixin):
    """Normalized SEC filing stored for chunking, retrieval, and citation."""

    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("accession_number", name="uq_source_documents_accession_number"),
        Index("ix_source_documents_ticker_fiscal_year", "ticker", "fiscal_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    # SEC EDGAR metadata
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    cik: Mapped[str] = mapped_column(String(10), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    form: Mapped[str] = mapped_column(String(16), nullable=False)        # "10-K" or "10-Q"
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_date: Mapped[date | None] = mapped_column(Date)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    accession_number: Mapped[str] = mapped_column(String(25), nullable=False)

    user: Mapped[User] = relationship(back_populates="source_documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(back_populates="document")
