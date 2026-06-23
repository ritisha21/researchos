"""
app/routes/papers.py
─────────────────────
FastAPI router for all paper-related endpoints.

Rate limits applied to every Gemini-backed endpoint (summarise, explain,
notes, takeaways, literature-review) since each one is a real LLM call —
uncontrolled traffic here burns through API quota fast. Search is also
limited, lighter touch, since it hits external APIs (Semantic Scholar,
arXiv) that have their own rate limits we don't want to trip.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.rate_limit import limiter
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
# SEARCH  — 30/minute (external API calls, lighter cost than Gemini)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/search", response_model=PaperSearchResponse, summary="Search papers (GET)")
@limiter.limit("30/minute")
async def search_papers_get(
    request: Request,
    q: str = Query(..., min_length=2, max_length=512, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
    sort_by: SearchSortBy = Query(default=SearchSortBy.RELEVANCE),
    db: AsyncSession = Depends(get_db),
) -> PaperSearchResponse:
    logger.info("route.papers.search_get", query=q)
    body = PaperSearchRequest(query=q, limit=limit, sort_by=sort_by)
    return await _do_search(body, db)


@router.post("/search", response_model=PaperSearchResponse, summary="Search papers (POST)")
@limiter.limit("30/minute")
async def search_papers_post(
    request: Request,
    body: PaperSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> PaperSearchResponse:
    logger.info("route.papers.search_post", query=body.query)
    return await _do_search(body, db)


@router.get("/{paper_id}", response_model=PaperInDB, summary="Get paper by UUID")
async def get_paper(paper_id: UUID, db: AsyncSession = Depends(get_db)) -> PaperInDB:
    paper = await paper_service.get_by_id(paper_id, db)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found.")
    return PaperInDB.model_validate(paper)


# ══════════════════════════════════════════════════════════════════════════════
# AI ANALYSIS  — 10/minute each (Gemini-backed, expensive)
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/summarise",
    response_model=SummariseResponse,
    summary="Summarise a paper",
    description="Generate summary, contributions, limitations, future work. Cached. **Rate limit: 10/min.**",
)
@limiter.limit("10/minute")
async def summarise_paper(
    request: Request,
    body: SummariseRequest,
    db: AsyncSession = Depends(get_db),
) -> SummariseResponse:
    logger.info("route.papers.summarise", title=body.title)
    try:
        return await paper_service.summarise(
            title=body.title, abstract=body.abstract,
            force_refresh=body.force_refresh, db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain a paper to a beginner",
    description="Beginner-friendly explanation. Cached. **Rate limit: 10/min.**",
)
@limiter.limit("10/minute")
async def explain_paper(
    request: Request,
    body: ExplainRequest,
    db: AsyncSession = Depends(get_db),
) -> ExplainResponse:
    logger.info("route.papers.explain", title=body.title)
    try:
        return await paper_service.explain(
            title=body.title, abstract=body.abstract,
            force_refresh=body.force_refresh, db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/notes",
    response_model=NotesResponse,
    summary="Generate study notes for a paper",
    description="8-12 structured study notes. **Rate limit: 10/min.**",
)
@limiter.limit("10/minute")
async def generate_notes(
    request: Request,
    body: NotesRequest,
    db: AsyncSession = Depends(get_db),
) -> NotesResponse:
    logger.info("route.papers.notes", title=body.title)
    try:
        return await paper_service.notes(
            title=body.title, abstract=body.abstract,
            force_refresh=body.force_refresh, db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/takeaways",
    response_model=TakeawaysResponse,
    summary="Extract key takeaways from a paper",
    description="5-8 practical takeaways. **Rate limit: 10/min.**",
)
@limiter.limit("10/minute")
async def generate_takeaways(
    request: Request,
    body: TakeawaysRequest,
    db: AsyncSession = Depends(get_db),
) -> TakeawaysResponse:
    logger.info("route.papers.takeaways", title=body.title)
    try:
        return await paper_service.takeaways(
            title=body.title, abstract=body.abstract,
            force_refresh=body.force_refresh, db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/literature-review",
    response_model=LiteratureReviewResponse,
    summary="Generate a literature review across multiple papers",
    description="Cohesive review across 1-10 papers. **Rate limit: 5/min** (most expensive call — multiple papers per request).",
)
@limiter.limit("5/minute")
async def literature_review(
    request: Request,
    body: LiteratureReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> LiteratureReviewResponse:
    logger.info("route.papers.literature_review", n=len(body.titles))
    try:
        return await paper_service.literature_review(body, db)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ── Shared ─────────────────────────────────────────────────────────────────────

async def _do_search(body: PaperSearchRequest, db: AsyncSession) -> PaperSearchResponse:
    try:
        return await search_service.search(body, db)
    except Exception as exc:
        logger.error("route.papers.search_error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Search failed: {exc}") from exc
