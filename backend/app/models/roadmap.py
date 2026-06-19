"""
app/models/roadmap.py
──────────────────────
ORM model for a generated research learning roadmap.
Each roadmap is keyed by topic and caches the Gemini-generated content
so repeated requests for the same topic skip the LLM call.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Roadmap(Base):
    __tablename__ = "roadmaps"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Topic ─────────────────────────────────────────────────────────────────
    # Stored normalised (lowercase, stripped) for cache lookup
    topic: Mapped[str] = mapped_column(String(512), nullable=False, index=True, unique=True)
    # Original casing from the user request
    topic_display: Mapped[str] = mapped_column(String(512), nullable=False)

    # ── Roadmap sections (JSON arrays / objects) ───────────────────────────────
    # Each field stores a list of dicts or strings serialised as JSONB.
    prerequisites: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    learning_path: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    foundational_papers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    intermediate_papers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    advanced_papers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    research_frontiers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    research_gaps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recommended_reading_order: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # ── Meta ──────────────────────────────────────────────────────────────────
    # Which LLM model generated this (for cache invalidation when model changes)
    generated_by_model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)

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
        return f"<Roadmap topic={self.topic!r}>"
