"""
app/routes/roadmap.py
──────────────────────
FastAPI router for the /roadmap endpoint.

POST /roadmap
  → Accepts a topic, returns a full research learning roadmap.

The route is intentionally thin: it validates input (Pydantic),
delegates to the service layer, and serialises output.
All business logic lives in services/roadmap_service.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.rate_limit import limiter
from app.schemas.roadmap import RoadmapRequest, RoadmapResponse
from app.services.roadmap_service import roadmap_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/roadmap", tags=["Research Navigator"])


@router.post(
    "",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a research learning roadmap",
    description=(
        "Given a research topic (e.g. 'Computer Vision'), returns a structured "
        "learning roadmap including prerequisites, foundational → advanced papers, "
        "research frontiers, and open problems. "
        "Results are cached in PostgreSQL; use `force_refresh=true` to regenerate.\n\n"
        "**Rate limit:** 10 requests/minute per IP (Gemini-backed, uncached requests are expensive)."
    ),
)
@limiter.limit("10/minute")
async def generate_roadmap(
    request: Request,
    body: RoadmapRequest,
    db: AsyncSession = Depends(get_db),
) -> RoadmapResponse:
    logger.info("route.roadmap.post", topic=body.topic)

    try:
        roadmap = await roadmap_service.generate_roadmap(body, db)
    except ValueError as exc:
        # LLM returned malformed output
        logger.error("route.roadmap.value_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse AI-generated roadmap: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("route.roadmap.unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the roadmap.",
        ) from exc

    return roadmap