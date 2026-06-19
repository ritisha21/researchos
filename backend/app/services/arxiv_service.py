"""
app/services/arxiv_service.py
──────────────────────────────
Async wrapper around the `arxiv` Python library.

The official arxiv library is synchronous, so we run it in a thread pool
(asyncio.to_thread) to avoid blocking the event loop.

Docs: https://lukasschwab.me/arxiv.py/index.html
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import arxiv

from app.config import settings
from app.schemas.paper import PaperSearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ArxivService:
    """
    Async interface to the arXiv search API.

    ArXiv is open — no API key required.
    Rate limit: ~3 req/sec; the library handles polite delays automatically.
    """

    def __init__(self) -> None:
        # Reuse a single Client instance for connection pooling
        self._client = arxiv.Client(
            page_size=settings.arxiv_max_results,
            delay_seconds=3.0,   # Polite delay between requests
            num_retries=3,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def search_papers(
        self,
        query: str,
        max_results: int | None = None,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
    ) -> list[PaperSearchResult]:
        """
        Search arXiv for papers matching the query.

        Args:
            query:       arXiv query string (supports field specifiers like ti:, abs:)
            max_results: Override the default from settings.
            sort_by:     Sorting criterion — Relevance | SubmittedDate | LastUpdatedDate

        Returns:
            List of PaperSearchResult objects.
        """
        limit = max_results or settings.arxiv_max_results
        logger.info("arxiv.search", query=query, limit=limit)

        search = arxiv.Search(
            query=query,
            max_results=limit,
            sort_by=sort_by,
        )

        # Run synchronous iterator in a thread pool to keep event loop free
        results: list[arxiv.Result] = await asyncio.to_thread(
            lambda: list(self._client.results(search))
        )

        papers = [self._parse_result(r) for r in results]
        logger.info("arxiv.search.done", count=len(papers))
        return papers

    async def get_paper_by_id(self, arxiv_id: str) -> PaperSearchResult | None:
        """
        Fetch a single paper by its arXiv ID (e.g. "1512.03385").
        Returns None if not found.
        """
        logger.info("arxiv.get_paper", arxiv_id=arxiv_id)
        search = arxiv.Search(id_list=[arxiv_id])
        results: list[arxiv.Result] = await asyncio.to_thread(
            lambda: list(self._client.results(search))
        )
        if not results:
            return None
        return self._parse_result(results[0])

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_result(result: arxiv.Result) -> PaperSearchResult:
        """Convert an arxiv.Result object into our PaperSearchResult schema."""
        # arXiv IDs look like "http://arxiv.org/abs/1512.03385v1"
        short_id = result.get_short_id()       # "1512.03385v1"
        base_id = short_id.split("v")[0]       # "1512.03385"

        year: int | None = None
        if result.published:
            published = result.published
            if isinstance(published, datetime):
                year = published.year

        return PaperSearchResult(
            title=result.title,
            authors=[a.name for a in result.authors],
            year=year,
            abstract=result.summary,
            citation_count=0,        # arXiv doesn't expose citation counts
            url=result.entry_id,     # "https://arxiv.org/abs/..."
            source="arxiv",
            external_id=base_id,
            arxiv_id=base_id,
            doi=result.doi,
        )


# Module-level singleton
arxiv_service = ArxivService()
