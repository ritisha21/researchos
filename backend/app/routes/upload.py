"""
app/routes/upload.py
─────────────────────
Phase 4 — PDF Upload & Indexing

POST /api/v1/upload
  Accepts a PDF file + optional metadata.
  Runs the full pipeline: extract → chunk → embed → store in ChromaDB.
  Creates/updates a Paper record in PostgreSQL.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db
from app.models.paper import Paper
from app.rate_limit import limiter
from app.services.pdf_service import pdf_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/upload", tags=["Phase 4 — PDF Upload"])

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a PDF paper",
    description=(
        "Upload a research paper PDF. The system will:\n"
        "1. Save the file to disk\n"
        "2. Extract text (pypdf + pdfplumber fallback)\n"
        "3. Chunk into overlapping segments\n"
        "4. Embed via Gemini and store in ChromaDB\n"
        "5. Create a Paper record in PostgreSQL\n\n"
        "Returns the paper_id to use with the /chat endpoint.\n\n"
        "**Rate limit:** 5 uploads/minute per IP (PDF extraction + embedding is costly)."
    ),
)
@limiter.limit("5/minute")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(..., description="PDF file to upload"),
    title: str = Form(..., description="Paper title"),
    authors: str = Form(default="", description="Comma-separated author names"),
    year: int | None = Form(default=None),
    abstract: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    # ── Validate file type ─────────────────────────────────────────────────────
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES and not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted.",
        )

    # ── Read file ──────────────────────────────────────────────────────────────
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB.",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # ── Create Paper record ────────────────────────────────────────────────────
    paper_id = str(uuid.uuid4())
    author_list = [a.strip() for a in authors.split(",") if a.strip()] if authors else []

    paper = Paper(
        id=uuid.UUID(paper_id),
        title=title.strip(),
        authors=author_list,
        year=year,
        abstract=abstract,
        source="upload",
        has_pdf=True,
        is_indexed=False,
    )
    db.add(paper)
    await db.flush()

    logger.info("upload.paper_created", paper_id=paper_id, title=title)

    # ── Run PDF pipeline ───────────────────────────────────────────────────────
    try:
        result = await pdf_service.process_pdf(
            file_bytes=file_bytes,
            paper_id=paper_id,
            filename=file.filename or f"{paper_id}.pdf",
        )
    except ValueError as exc:
        # Extraction failed — clean up the paper record
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("upload.pipeline_failed", paper_id=paper_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF processing failed. Please try again.",
        ) from exc

    # ── Mark as indexed ────────────────────────────────────────────────────────
    paper.pdf_path = result["saved_path"]
    paper.is_indexed = True
    await db.flush()

    return {
        "paper_id": paper_id,
        "title": title,
        "chunks_indexed": result["chunks"],
        "file_size_bytes": file_size,
        "message": "PDF uploaded and indexed successfully. Use paper_id with /api/v1/chat.",
    }
