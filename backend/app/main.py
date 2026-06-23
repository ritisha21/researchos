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
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.rate_limit import limiter
from app.utils.logger import configure_logging, get_logger

# Configure logging FIRST before anything else
configure_logging()
logger = get_logger(__name__)

from app.database.base import import_all_models
from app.database.session import engine
from app.routes import chat, health, papers, roadmap, upload


async def run_migrations() -> None:
    """
    Run Alembic migrations programmatically at startup.

    This runs `alembic upgrade head` using the sync driver in a thread,
    since Alembic's migration runner is synchronous. Safe to call on every
    startup — Alembic tracks applied versions in the alembic_version table
    and is a no-op if already up to date.
    """
    import asyncio
    from alembic import command
    from alembic.config import Config

    def _upgrade():
        cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        # Use the sync psycopg2 URL for Alembic (it doesn't support asyncpg directly)
        sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(cfg, "head")

    await asyncio.to_thread(_upgrade)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("researchos.startup", version="1.1.0", env=settings.app_env)

    import_all_models()

    # Run Alembic migrations instead of create_all().
    # create_all() only adds missing tables — it never alters existing
    # columns, which silently causes schema drift in production. Alembic
    # tracks every change as a versioned, reversible migration.
    await run_migrations()
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

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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