"""
app/main.py — Fixed: configure_logging() called before any imports that log,
removed logger.info() call that happened before logging was configured.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.utils.logger import configure_logging, get_logger

# Configure logging FIRST before anything else
configure_logging()
logger = get_logger(__name__)

from app.database.base import import_all_models
from app.database.session import engine
from app.routes import chat, health, papers, roadmap, upload


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("researchos.startup", version="1.0.0", env=settings.app_env)

    import_all_models()

    from app.database.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("researchos.db.ready")

    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)

    yield

    logger.info("researchos.shutdown")
    await engine.dispose()

    from app.services.semantic_scholar import semantic_scholar_service
    await semantic_scholar_service.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ResearchOS",
        description=(
            "**ResearchOS** — AI-powered research learning platform\n\n"
            "| Phase | Feature | Endpoint |\n"
            "|---|---|---|\n"
            "| 1 | Research Navigator | `POST /api/v1/roadmap` |\n"
            "| 2 | Paper Search | `GET/POST /api/v1/papers/search` |\n"
            "| 3 | Paper Analysis | `POST /api/v1/papers/summarise` etc. |\n"
            "| 4 | PDF Upload | `POST /api/v1/upload` |\n"
            "| 5 | Paper Chat | `POST /api/v1/chat` |\n"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )

    v1 = "/api/v1"
    app.include_router(health.router)
    app.include_router(roadmap.router, prefix=v1)
    app.include_router(papers.router,  prefix=v1)
    app.include_router(upload.router,  prefix=v1)
    app.include_router(chat.router,    prefix=v1)

    return app


app = create_app()
