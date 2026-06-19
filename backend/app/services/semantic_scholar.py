"""
app/services/semantic_scholar.py
──────────────────────────────────
Async client for the Semantic Scholar Graph API.

Docs: https://api.semanticscholar.org/api-docs/

Key decisions
─────────────
* Uses httpx.AsyncClient for non-blocking I/O — fits naturally in FastAPI.
* tenacity retries on transient 429 / 5xx errors with exponential back-off.
* Fields are requested explicitly to minimise payload size.
* The free tier allows ~100 requests / 5 min; an API key raises this limit.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.schemas.paper import PaperSearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Fields we request from every paper endpoint
PAPER_FIELDS = ",".join([
    "paperId",
    "title",
    "authors",
    "year",
    "abstract",
    "citationCount",
    "externalIds",
    "url",
])


class SemanticScholarError(Exception):
    """Raised when the Semantic Scholar API returns an unexpected response."""


class SemanticScholarService:
    """
    Thin async wrapper around the Semantic Scholar Graph API v1.

    Instantiate once per application (singleton via dependency injection
    or module-level instance) — it owns the shared httpx.AsyncClient.
    """

    def __init__(self) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key

        self._client = httpx.AsyncClient(
            base_url=settings.semantic_scholar_base_url,
            headers=headers,
            timeout=httpx.Timeout(30.0),
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def search_papers(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[PaperSearchResult]:
        """
        Full-text search for papers.

        Args:
            query:  Free-text query, e.g. "deep residual learning image recognition"
            limit:  Max results to return (1–100).
            offset: Pagination offset.

        Returns:
            List of PaperSearchResult objects.
        """
        logger.info("semantic_scholar.search", query=query, limit=limit)

        data = await self._get(
            "/paper/search",
            params={
                "query": query,
                "limit": min(limit, 100),
                "offset": offset,
                "fields": PAPER_FIELDS,
            },
        )

        papers = [self._parse_paper(p) for p in data.get("data", [])]
        logger.info("semantic_scholar.search.done", count=len(papers))
        return papers

    async def get_paper_by_id(self, paper_id: str) -> PaperSearchResult | None:
        """
        Fetch a single paper by its Semantic Scholar paper ID.
        Returns None if the paper is not found.
        """
        logger.info("semantic_scholar.get_paper", paper_id=paper_id)
        try:
            data = await self._get(f"/paper/{paper_id}", params={"fields": PAPER_FIELDS})
            return self._parse_paper(data)
        except SemanticScholarError as e:
            if "404" in str(e):
                return None
            raise

    async def get_paper_recommendations(
        self,
        paper_id: str,
        limit: int = 5,
    ) -> list[PaperSearchResult]:
        """
        Get papers recommended based on a seed paper.
        Uses the Recommendations API endpoint.
        """
        logger.info("semantic_scholar.recommendations", paper_id=paper_id)
        data = await self._get(
            f"/paper/{paper_id}/recommendations",
            params={"fields": PAPER_FIELDS, "limit": limit},
        )
        return [self._parse_paper(p) for p in data.get("recommendedPapers", [])]

    async def close(self) -> None:
        """Cleanly close the underlying HTTP client. Call at app shutdown."""
        await self._client.aclose()

    # ── Private helpers ────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Execute a GET request and return parsed JSON, with retries."""
        response = await self._client.get(path, params=params)

        if response.status_code == 429:
            # Rate limited — wait and retry
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning("semantic_scholar.rate_limited", retry_after=retry_after)
            await asyncio.sleep(retry_after)
            response = await self._client.get(path, params=params)

        if response.status_code != 200:
            raise SemanticScholarError(
                f"Semantic Scholar API error {response.status_code}: {response.text[:200]}"
            )

        return response.json()

    @staticmethod
    def _parse_paper(raw: dict) -> PaperSearchResult:
        """Convert a raw Semantic Scholar paper dict into a PaperSearchResult."""
        external_ids: dict = raw.get("externalIds") or {}
        authors = [a.get("name", "") for a in raw.get("authors") or []]

        return PaperSearchResult(
            title=raw.get("title") or "Untitled",
            authors=authors,
            year=raw.get("year"),
            abstract=raw.get("abstract"),
            citation_count=raw.get("citationCount") or 0,
            url=raw.get("url"),
            source="semantic_scholar",
            external_id=raw.get("paperId") or "",
            semantic_scholar_id=raw.get("paperId"),
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
        )


# Module-level singleton — shared across the application lifetime
semantic_scholar_service = SemanticScholarService()
