"""
app/schemas/roadmap.py
───────────────────────
Pydantic v2 schemas for the /roadmap endpoint.
These are the API contract — completely separate from the ORM models.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Nested schemas ────────────────────────────────────────────────────────────

class PaperReference(BaseModel):
    """A paper mentioned inside a roadmap section."""
    title: str
    authors: list[str] = []
    year: int | None = None
    url: str | None = None
    why_important: str | None = Field(
        default=None,
        description="One sentence on why this paper belongs at this level.",
    )


class LearningStep(BaseModel):
    """A single step in the ordered learning path."""
    order: int
    topic: str
    description: str
    estimated_hours: int | None = None


# ── Request ───────────────────────────────────────────────────────────────────

class RoadmapRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=2,
        max_length=512,
        examples=["Computer Vision", "Reinforcement Learning"],
        description="The research area for which to generate a learning roadmap.",
    )
    force_refresh: bool = Field(
        default=False,
        description="If true, bypass the cache and regenerate the roadmap.",
    )

    @field_validator("topic")
    @classmethod
    def strip_topic(cls, v: str) -> str:
        return v.strip()


# ── Response ──────────────────────────────────────────────────────────────────

class RoadmapResponse(BaseModel):
    id: UUID
    topic: str
    topic_display: str

    # Core content
    prerequisites: list[str]
    learning_path: list[LearningStep]
    foundational_papers: list[PaperReference]
    intermediate_papers: list[PaperReference]
    advanced_papers: list[PaperReference]
    research_frontiers: list[str]
    research_gaps: list[str]
    recommended_reading_order: list[str]

    # Meta
    generated_by_model: str
    cached: bool = Field(
        default=False,
        description="True when the response was served from the database cache.",
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
