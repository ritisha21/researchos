"""
app/models/paper.py
────────────────────
ORM model representing a research paper stored in PostgreSQL.
Covers both manually entered papers and uploaded PDFs.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Paper(Base):
    __tablename__ = "papers"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Bibliographic metadata ────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    authors: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    semantic_scholar_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # ── Source tracking ───────────────────────────────────────────────────────
    # How was this paper added?  'upload' | 'manual' | 'semantic_scholar' | 'arxiv'
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")

    # ── PDF upload ────────────────────────────────────────────────────────────
    has_pdf: Mapped[bool] = mapped_column(Boolean, default=False)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # True once the PDF has been chunked and embedded into ChromaDB
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── AI-generated content (cached) ─────────────────────────────────────────
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_contributions: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    future_work: Mapped[str | None] = mapped_column(Text, nullable=True)
    beginner_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Paper id={self.id} title={self.title!r}>"
