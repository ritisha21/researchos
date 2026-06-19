"""
app/routes/papers.py
─────────────────────
FastAPI router for all paper-related endpoints.

Phase 2:
  GET  /api/v1/papers/search          — quick search via URL params
  POST /api/v1/papers/search          — full search with options
  GET  /api/v1/papers/{id}            — get saved paper by UUID

Phase 3:
  POST /api/v1/papers/summarise       — summary + contributions + limitations
  POST /api/v1/papers/explain         — beginner-friendly explanation
  POST /api/v1/papers/notes           — structured study notes
  POST /api/v1/papers/takeaways       — key practical takeaways
  POST /api/v1/papers/literature-review — multi-paper literature review
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.paper import (
    ExplainRequest,
    ExplainResponse,
    LiteratureReviewRequest,
    LiteratureReviewResponse,
    NotesRequest,
    NotesResponse,
    PaperInDB,
    PaperSearchRequest,
    PaperSearchResponse,
    SearchSortBy,
    SummariseRequest,
    SummariseResponse,
    TakeawaysRequest,
    TakeawaysResponse,
)
from app.services.paper_service import paper_service
from app.services.search_service import search_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/papers", tags=["Research Assistant — Papers"])


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — SEARCH
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/search",
    response_model=PaperSearchResponse,
    summary="Search papers (GET)",
)
async def search_papers_get(
    q: str = Query(..., min_length=2, max_length=512, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
    sort_by: SearchSortBy = Query(default=SearchSortBy.RELEVANCE),
    db: AsyncSession = Depends(get_db),
) -> PaperSearchResponse:
    logger.info("route.papers.search_get", query=q)
    request = PaperSearchRequest(query=q, limit=limit, sort_by=sort_by)
    return await _do_search(request, db)


@router.post(
    "/search",
    response_model=PaperSearchResponse,
    summary="Search papers (POST)",
)
async def search_papers_post(
    request: PaperSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> PaperSearchResponse:
    logger.info("route.papers.search_post", query=request.query)
    return await _do_search(request, db)


@router.get(
    "/{paper_id}",
    response_model=PaperInDB,
    summary="Get paper by UUID",
)
async def get_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PaperInDB:
    paper = await paper_service.get_by_id(paper_id, db)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found.")
    return PaperInDB.model_validate(paper)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — AI ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/summarise",
    response_model=SummariseResponse,
    summary="Summarise a paper",
    description=(
        "Generate a summary, key contributions, limitations, and future work "
        "for a paper given its title and optional abstract. "
        "Results are cached — use `force_refresh=true` to regenerate."
    ),
)
async def summarise_paper(
    request: SummariseRequest,
    db: AsyncSession = Depends(get_db),
) -> SummariseResponse:
    logger.info("route.papers.summarise", title=request.title)
    try:
        return await paper_service.summarise(
            title=request.title,
            abstract=request.abstract,
            force_refresh=request.force_refresh,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain a paper to a beginner",
    description=(
        "Generate a plain-English, beginner-friendly explanation of a paper "
        "using analogies and simple language. Cached per paper."
    ),
)
async def explain_paper(
    request: ExplainRequest,
    db: AsyncSession = Depends(get_db),
) -> ExplainResponse:
    logger.info("route.papers.explain", title=request.title)
    try:
        return await paper_service.explain(
            title=request.title,
            abstract=request.abstract,
            force_refresh=request.force_refresh,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/notes",
    response_model=NotesResponse,
    summary="Generate study notes for a paper",
    description="Generate 8-12 concise, structured study notes for a paper.",
)
async def generate_notes(
    request: NotesRequest,
    db: AsyncSession = Depends(get_db),
) -> NotesResponse:
    logger.info("route.papers.notes", title=request.title)
    try:
        return await paper_service.notes(
            title=request.title,
            abstract=request.abstract,
            force_refresh=request.force_refresh,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/takeaways",
    response_model=TakeawaysResponse,
    summary="Extract key takeaways from a paper",
    description="Extract 5-8 practical, memorable takeaways from a paper.",
)
async def generate_takeaways(
    request: TakeawaysRequest,
    db: AsyncSession = Depends(get_db),
) -> TakeawaysResponse:
    logger.info("route.papers.takeaways", title=request.title)
    try:
        return await paper_service.takeaways(
            title=request.title,
            abstract=request.abstract,
            force_refresh=request.force_refresh,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/literature-review",
    response_model=LiteratureReviewResponse,
    summary="Generate a literature review across multiple papers",
    description=(
        "Given 1-10 paper titles (and optional abstracts), generate a cohesive "
        "literature review covering themes, connections, gaps, and reading order."
    ),
)
async def literature_review(
    request: LiteratureReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> LiteratureReviewResponse:
    logger.info("route.papers.literature_review", n=len(request.titles))
    try:
        return await paper_service.literature_review(request, db)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ── Shared ─────────────────────────────────────────────────────────────────────

async def _do_search(request: PaperSearchRequest, db: AsyncSession) -> PaperSearchResponse:
    try:
        return await search_service.search(request, db)
    except Exception as exc:
        logger.error("route.papers.search_error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Search failed: {exc}") from exc
