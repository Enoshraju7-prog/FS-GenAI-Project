from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.document_chunks import DocumentChunk
    from app.database.models.document_tables import DocumentTable


class SourceDocument(Base, TimestampMixin):
    """Normalized SEC filing stored for chunking, retrieval, and citation."""

    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("accession_number", name="uq_source_documents_accession_number"),
        Index("ix_source_documents_ticker_fiscal_year", "ticker", "fiscal_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # SEC EDGAR metadata
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    cik: Mapped[str] = mapped_column(String(10), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    form: Mapped[str] = mapped_column(String(16), nullable=False)        # "10-K" or "10-Q"
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_date: Mapped[date | None] = mapped_column(Date)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    accession_number: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_document: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Ingested content
    markdown_content: Mapped[str | None] = mapped_column(Text)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    tables: Mapped[list[DocumentTable]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
