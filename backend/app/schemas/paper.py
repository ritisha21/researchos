"""
app/schemas/paper.py
─────────────────────
Pydantic v2 schemas for all paper-related API endpoints.
Phase 2: search
Phase 3: summarise, explain, notes, takeaways, literature review
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class PaperSource(str, Enum):
    SEMANTIC_SCHOLAR = "semantic_scholar"
    ARXIV = "arxiv"
    UPLOAD = "upload"
    MANUAL = "manual"


class SearchSortBy(str, Enum):
    RELEVANCE = "relevance"
    CITATION_COUNT = "citation_count"
    YEAR = "year"


# ── Shared base ───────────────────────────────────────────────────────────────

class PaperBase(BaseModel):
    title: str
    authors: list[str] = []
    year: int | None = None
    abstract: str | None = None
    citation_count: int = 0
    url: str | None = None


# ── Search schemas (Phase 2) ──────────────────────────────────────────────────

class PaperSearchResult(PaperBase):
    source: PaperSource
    external_id: str
    doi: str | None = None
    arxiv_id: str | None = None
    semantic_scholar_id: str | None = None


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=512)
    limit: int = Field(default=10, ge=1, le=50)
    sources: list[PaperSource] = Field(
        default=[PaperSource.SEMANTIC_SCHOLAR, PaperSource.ARXIV]
    )
    sort_by: SearchSortBy = Field(default=SearchSortBy.RELEVANCE)
    save_results: bool = Field(default=True)


class PaperSearchResponse(BaseModel):
    query: str
    total_results: int
    sources_queried: list[str]
    results: list[PaperSearchResult]


# ── Summarisation schemas (Phase 3) ──────────────────────────────────────────

class SummariseRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=512)
    abstract: str | None = Field(default=None)
    force_refresh: bool = Field(default=False)


class SummariseResponse(BaseModel):
    title: str
    summary: str
    key_contributions: list[str]
    limitations: list[str]
    future_work: list[str]
    cached: bool = False


class ExplainRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=512)
    abstract: str | None = None
    force_refresh: bool = False


class ExplainResponse(BaseModel):
    title: str
    explanation: str
    cached: bool = False


class NotesRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=512)
    abstract: str | None = None
    force_refresh: bool = False


class NotesResponse(BaseModel):
    title: str
    notes: list[str]
    cached: bool = False


class TakeawaysRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=512)
    abstract: str | None = None
    force_refresh: bool = False


class TakeawaysResponse(BaseModel):
    title: str
    takeaways: list[str]
    cached: bool = False


class LiteratureReviewRequest(BaseModel):
    titles: list[str] = Field(..., min_length=1, max_length=10)
    abstracts: list[str] | None = None
    focus: str | None = Field(
        default=None,
        description="Optional focus area, e.g. 'compare architectures'",
    )


class LiteratureReviewResponse(BaseModel):
    papers_reviewed: int
    review: str
    themes: list[str]
    gaps: list[str]
    recommended_reading_order: list[str]


# ── DB record schema ──────────────────────────────────────────────────────────

class PaperInDB(PaperBase):
    id: UUID
    source: str
    doi: str | None = None
    arxiv_id: str | None = None
    semantic_scholar_id: str | None = None
    has_pdf: bool
    is_indexed: bool
    summary: str | None = None
    key_contributions: str | None = None
    limitations: str | None = None
    future_work: str | None = None
    beginner_explanation: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
