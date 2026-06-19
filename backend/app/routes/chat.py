"""
app/routes/chat.py
───────────────────
Phase 5 — Paper Chat with Citations

POST /api/v1/chat
  Accepts a paper_id (from /upload) and a question.
  Returns an answer grounded in the paper's content, with citations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service
from app.services.paper_service import paper_service
from app.utils.logger import get_logger
import uuid

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Phase 5 — Paper Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Chat with an uploaded paper",
    description=(
        "Ask any question about an uploaded and indexed PDF paper.\n\n"
        "- `paper_id`: the UUID returned by `POST /api/v1/upload`\n"
        "- `question`: your question about the paper\n"
        "- `conversation_history`: optional prior messages for multi-turn chat\n\n"
        "Returns an answer with inline citations referencing specific sections "
        "of the paper."
    ),
)
async def chat_with_paper(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    logger.info("route.chat", paper_id=request.paper_id, question=request.question[:80])

    # Validate paper exists and is indexed
    try:
        paper_uuid = uuid.UUID(request.paper_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid paper_id format. Must be a UUID.",
        )

    paper = await paper_service.get_by_id(paper_uuid, db)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper {request.paper_id} not found. Upload it first via POST /api/v1/upload.",
        )
    if not paper.is_indexed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper exists but has not been indexed yet. Please wait or re-upload.",
        )

    try:
        return await chat_service.chat(request)
    except Exception as exc:
        logger.error("route.chat.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {exc}",
        ) from exc
