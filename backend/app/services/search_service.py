"""
app/services/search_service.py
───────────────────────────────
Orchestrates paper search across multiple sources:

  1. Fan out queries to Semantic Scholar AND/OR arXiv concurrently
  2. Deduplicate results (same arXiv ID or title similarity)
  3. Merge and sort by the requested strategy
  4. Optionally persist new papers to PostgreSQL

Design notes
────────────
- asyncio.gather() runs both API calls concurrently — halves latency.
- Deduplication uses a two-pass approach:
    Pass 1: exact match on arxiv_id or semantic_scholar_id
    Pass 2: normalised title match (lowercased, punctuation stripped)
- Citation count sort only meaningful for Semantic Scholar results
  (arXiv doesn't expose citation counts).
"""

from __future__ import annotations

import asyncio
import re
import unicodedata

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.paper import (
    PaperSearchRequest,
    PaperSearchResponse,
    PaperSearchResult,
    PaperSource,
    SearchSortBy,
)
from app.services.arxiv_service import arxiv_service
from app.services.paper_service import paper_service
from app.services.semantic_scholar import semantic_scholar_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _normalise_title(title: str) -> str:
    """Lowercase, strip accents and punctuation for fuzzy dedup."""
    nfkd = unicodedata.normalize("NFKD", title.lower())
    ascii_str = nfkd.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", "", ascii_str).strip()


class SearchService:
    """Fan-out search across Semantic Scholar and arXiv."""

    async def search(
        self,
        request: PaperSearchRequest,
        db: AsyncSession,
    ) -> PaperSearchResponse:
        sources_queried: list[str] = []
        tasks: list[asyncio.Task] = []

        # ── 1. Build concurrent tasks ──────────────────────────────────────────
        async def _ss_search() -> list[PaperSearchResult]:
            results = await semantic_scholar_service.search_papers(
                query=request.query,
                limit=request.limit,
            )
            return results

        async def _arxiv_search() -> list[PaperSearchResult]:
            results = await arxiv_service.search_papers(
                query=request.query,
                max_results=request.limit,
            )
            return results

        coroutines = []
        if PaperSource.SEMANTIC_SCHOLAR in request.sources:
            sources_queried.append("semantic_scholar")
            coroutines.append(_ss_search())

        if PaperSource.ARXIV in request.sources:
            sources_queried.append("arxiv")
            coroutines.append(_arxiv_search())

        logger.info(
            "search_service.fan_out",
            query=request.query,
            sources=sources_queried,
        )

        # ── 2. Run concurrently, tolerate individual failures ──────────────────
        raw_results_nested = await asyncio.gather(*coroutines, return_exceptions=True)

        all_results: list[PaperSearchResult] = []
        for source, outcome in zip(sources_queried, raw_results_nested):
            if isinstance(outcome, Exception):
                logger.error(
                    "search_service.source_failed",
                    source=source,
                    error=str(outcome),
                )
            else:
                all_results.extend(outcome)

        # ── 3. Deduplicate ─────────────────────────────────────────────────────
        deduped = self._deduplicate(all_results)
        logger.info(
            "search_service.dedup",
            before=len(all_results),
            after=len(deduped),
        )

        # ── 4. Sort ────────────────────────────────────────────────────────────
        sorted_results = self._sort(deduped, request.sort_by)

        # Truncate to requested limit after merge
        final = sorted_results[: request.limit]

        # ── 5. Optionally persist to PostgreSQL ───────────────────────────────
        if request.save_results and db is not None:
            await self._persist(final, db)

        return PaperSearchResponse(
            query=request.query,
            total_results=len(final),
            sources_queried=sources_queried,
            results=final,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(results: list[PaperSearchResult]) -> list[PaperSearchResult]:
        """
        Two-pass deduplication.

        Pass 1: exact ID match — if both Semantic Scholar and arXiv return
                the same paper (identified by shared arxiv_id), keep the
                Semantic Scholar version (has citation count).
        Pass 2: normalised title match — catches near-duplicates where one
                source has a slightly different title formatting.
        """
        seen_arxiv: dict[str, PaperSearchResult] = {}
        seen_ss: dict[str, PaperSearchResult] = {}
        seen_titles: dict[str, PaperSearchResult] = {}
        deduped: list[PaperSearchResult] = []

        for paper in results:
            # Pass 1a: deduplicate by arxiv_id
            if paper.arxiv_id:
                if paper.arxiv_id in seen_arxiv:
                    existing = seen_arxiv[paper.arxiv_id]
                    # Prefer Semantic Scholar entry (has citation count)
                    if (
                        paper.source == PaperSource.SEMANTIC_SCHOLAR
                        and existing.source == PaperSource.ARXIV
                    ):
                        # Replace in deduped list
                        idx = deduped.index(existing)
                        deduped[idx] = paper
                        seen_arxiv[paper.arxiv_id] = paper
                    continue
                seen_arxiv[paper.arxiv_id] = paper

            # Pass 1b: deduplicate by semantic_scholar_id
            if paper.semantic_scholar_id:
                if paper.semantic_scholar_id in seen_ss:
                    continue
                seen_ss[paper.semantic_scholar_id] = paper

            # Pass 2: normalised title match
            norm_title = _normalise_title(paper.title)
            if norm_title in seen_titles:
                continue
            seen_titles[norm_title] = paper

            deduped.append(paper)

        return deduped

    @staticmethod
    def _sort(
        results: list[PaperSearchResult],
        sort_by: SearchSortBy,
    ) -> list[PaperSearchResult]:
        if sort_by == SearchSortBy.CITATION_COUNT:
            return sorted(results, key=lambda p: p.citation_count, reverse=True)
        if sort_by == SearchSortBy.YEAR:
            return sorted(results, key=lambda p: p.year or 0, reverse=True)
        # RELEVANCE: preserve original order (sources already return by relevance)
        return results

    async def _persist(
        self,
        results: list[PaperSearchResult],
        db: AsyncSession,
    ) -> None:
        """Save each result to PostgreSQL if it doesn't already exist."""
        created_count = 0
        for result in results:
            try:
                _, created = await paper_service.get_or_create_from_search_result(
                    result, db
                )
                if created:
                    created_count += 1
            except Exception as exc:
                logger.warning(
                    "search_service.persist_failed",
                    title=result.title,
                    error=str(exc),
                )
        if created_count:
            logger.info("search_service.persisted", new_papers=created_count)


# Module-level singleton
search_service = SearchService()
