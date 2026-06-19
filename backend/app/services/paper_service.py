"""
app/services/paper_service.py
──────────────────────────────
Paper management service.
Phase 2: CRUD — get_or_create, get_by_id
Phase 3: summarise, explain, notes, takeaways, literature_review
         All results are cached back to the papers table.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.schemas.paper import (
    ExplainResponse,
    LiteratureReviewRequest,
    LiteratureReviewResponse,
    NotesResponse,
    PaperSearchResult,
    SummariseResponse,
    TakeawaysResponse,
)
from app.services.gemini import gemini_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Prompts ───────────────────────────────────────────────────────────────────

SUMMARISE_PROMPT = """\
You are an expert AI research assistant.

Analyse the following research paper and return ONLY a valid JSON object.

Title: {title}
Abstract: {abstract}

Return this exact JSON structure:
{{
  "summary": "3-5 sentence comprehensive summary of the paper",
  "key_contributions": [
    "First major contribution",
    "Second major contribution",
    "Third major contribution"
  ],
  "limitations": [
    "First limitation mentioned or implied",
    "Second limitation"
  ],
  "future_work": [
    "First future direction suggested",
    "Second future direction"
  ]
}}

Rules:
- summary: 3-5 sentences, technical but clear
- key_contributions: 3-6 items, each one sentence
- limitations: 2-4 items
- future_work: 2-4 items
- Base your response only on the title and abstract provided
- Do not fabricate specific numbers or claims not implied by the abstract
"""

EXPLAIN_PROMPT = """\
You are an expert at explaining complex research papers to beginners.

Explain the following research paper as if you are talking to someone who
knows basic programming but has never read a research paper before.
Use simple analogies. Avoid jargon. Be engaging and friendly.

Title: {title}
Abstract: {abstract}

Write 4-6 paragraphs. Do NOT return JSON — return plain readable text.
Start directly with the explanation. No preamble like "Sure!" or "Of course!".
"""

NOTES_PROMPT = """\
You are an expert AI research assistant creating study notes.

Generate concise, structured study notes for this research paper.

Title: {title}
Abstract: {abstract}

Return ONLY a valid JSON object:
{{
  "notes": [
    "Note 1: ...",
    "Note 2: ...",
    "Note 3: ..."
  ]
}}

Rules:
- 8-12 bullet-point style notes
- Each note is one clear, self-contained sentence
- Cover: problem statement, approach, method, results, significance
- Use past tense for what the paper did
"""

TAKEAWAYS_PROMPT = """\
You are an expert AI research assistant.

Extract the most important practical takeaways from this research paper —
things a researcher or engineer would want to remember and apply.

Title: {title}
Abstract: {abstract}

Return ONLY a valid JSON object:
{{
  "takeaways": [
    "Takeaway 1",
    "Takeaway 2"
  ]
}}

Rules:
- 5-8 takeaways
- Each is actionable or memorable — something worth writing on a sticky note
- Prioritise insights that transfer beyond this specific paper
"""

LITERATURE_REVIEW_PROMPT = """\
You are an expert AI research assistant writing a literature review.

You have been given {n} papers. Write a cohesive literature review.
{focus_line}

Papers:
{papers_block}

Return ONLY a valid JSON object:
{{
  "review": "The full literature review text, 4-6 paragraphs",
  "themes": [
    "Theme 1: ...",
    "Theme 2: ..."
  ],
  "gaps": [
    "Gap 1: ...",
    "Gap 2: ..."
  ],
  "recommended_reading_order": [
    "Paper title 1",
    "Paper title 2"
  ]
}}

Rules:
- review: 4-6 paragraphs, flowing prose, cite papers by title
- themes: 3-5 common themes across the papers
- gaps: 3-5 open problems or gaps the papers collectively leave
- recommended_reading_order: all paper titles in logical learning order
"""


class PaperService:
    """CRUD + AI-powered analysis for Paper records."""

    # ── Phase 2: CRUD ─────────────────────────────────────────────────────────

    async def get_or_create_from_search_result(
        self,
        result: PaperSearchResult,
        db: AsyncSession,
    ) -> tuple[Paper, bool]:
        existing = await self._find_existing(result, db)
        if existing:
            return existing, False

        paper = Paper(
            id=uuid.uuid4(),
            title=result.title,
            authors=result.authors,
            year=result.year,
            abstract=result.abstract,
            citation_count=result.citation_count,
            url=result.url,
            doi=result.doi,
            arxiv_id=result.arxiv_id,
            semantic_scholar_id=result.semantic_scholar_id,
            source=result.source,
        )
        db.add(paper)
        await db.flush()
        await db.refresh(paper)
        logger.info("paper_service.created", paper_id=str(paper.id))
        return paper, True

    async def get_by_id(self, paper_id: uuid.UUID, db: AsyncSession) -> Paper | None:
        result = await db.execute(select(Paper).where(Paper.id == paper_id))
        return result.scalar_one_or_none()

    # ── Phase 3: AI Analysis ──────────────────────────────────────────────────

    async def summarise(
        self,
        title: str,
        abstract: str | None,
        force_refresh: bool,
        db: AsyncSession,
    ) -> SummariseResponse:
        paper = await self._find_by_title(title, db)

        if paper and paper.summary and not force_refresh:
            logger.info("paper_service.summarise.cache_hit", title=title)
            return SummariseResponse(
                title=title,
                summary=paper.summary,
                key_contributions=json.loads(paper.key_contributions or "[]"),
                limitations=json.loads(paper.limitations or "[]"),
                future_work=json.loads(paper.future_work or "[]"),
                cached=True,
            )

        prompt = SUMMARISE_PROMPT.format(
            title=title,
            abstract=abstract or "Not provided.",
        )
        raw = await gemini_service.generate_json(prompt)
        data = self._parse_json(raw, "summarise")

        summary = data.get("summary", "")
        key_contributions = data.get("key_contributions", [])
        limitations = data.get("limitations", [])
        future_work = data.get("future_work", [])

        if paper:
            paper.summary = summary
            paper.key_contributions = json.dumps(key_contributions)
            paper.limitations = json.dumps(limitations)
            paper.future_work = json.dumps(future_work)
            await db.flush()

        return SummariseResponse(
            title=title,
            summary=summary,
            key_contributions=key_contributions,
            limitations=limitations,
            future_work=future_work,
            cached=False,
        )

    async def explain(
        self,
        title: str,
        abstract: str | None,
        force_refresh: bool,
        db: AsyncSession,
    ) -> ExplainResponse:
        paper = await self._find_by_title(title, db)

        if paper and paper.beginner_explanation and not force_refresh:
            logger.info("paper_service.explain.cache_hit", title=title)
            return ExplainResponse(
                title=title,
                explanation=paper.beginner_explanation,
                cached=True,
            )

        prompt = EXPLAIN_PROMPT.format(
            title=title,
            abstract=abstract or "Not provided.",
        )
        explanation = await gemini_service.generate(prompt)

        if paper:
            paper.beginner_explanation = explanation
            await db.flush()

        return ExplainResponse(title=title, explanation=explanation, cached=False)

    async def notes(
        self,
        title: str,
        abstract: str | None,
        force_refresh: bool,
        db: AsyncSession,
    ) -> NotesResponse:
        prompt = NOTES_PROMPT.format(
            title=title,
            abstract=abstract or "Not provided.",
        )
        raw = await gemini_service.generate_json(prompt)
        data = self._parse_json(raw, "notes")
        return NotesResponse(
            title=title,
            notes=data.get("notes", []),
            cached=False,
        )

    async def takeaways(
        self,
        title: str,
        abstract: str | None,
        force_refresh: bool,
        db: AsyncSession,
    ) -> TakeawaysResponse:
        prompt = TAKEAWAYS_PROMPT.format(
            title=title,
            abstract=abstract or "Not provided.",
        )
        raw = await gemini_service.generate_json(prompt)
        data = self._parse_json(raw, "takeaways")
        return TakeawaysResponse(
            title=title,
            takeaways=data.get("takeaways", []),
            cached=False,
        )

    async def literature_review(
        self,
        request: LiteratureReviewRequest,
        db: AsyncSession,
    ) -> LiteratureReviewResponse:
        abstracts = request.abstracts or []

        papers_block = ""
        for i, title in enumerate(request.titles):
            abstract = abstracts[i] if i < len(abstracts) else "Not provided."
            papers_block += f"\nPaper {i+1}:\nTitle: {title}\nAbstract: {abstract}\n"

        focus_line = (
            f"Focus specifically on: {request.focus}"
            if request.focus
            else "Cover methodology, findings, and connections between papers."
        )

        prompt = LITERATURE_REVIEW_PROMPT.format(
            n=len(request.titles),
            focus_line=focus_line,
            papers_block=papers_block,
        )
        raw = await gemini_service.generate_json(prompt)
        data = self._parse_json(raw, "literature_review")

        return LiteratureReviewResponse(
            papers_reviewed=len(request.titles),
            review=data.get("review", ""),
            themes=data.get("themes", []),
            gaps=data.get("gaps", []),
            recommended_reading_order=data.get("recommended_reading_order", []),
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _find_existing(
        self, result: PaperSearchResult, db: AsyncSession
    ) -> Paper | None:
        if result.semantic_scholar_id:
            r = await db.execute(
                select(Paper).where(Paper.semantic_scholar_id == result.semantic_scholar_id)
            )
            p = r.scalar_one_or_none()
            if p:
                return p
        if result.arxiv_id:
            r = await db.execute(
                select(Paper).where(Paper.arxiv_id == result.arxiv_id)
            )
            p = r.scalar_one_or_none()
            if p:
                return p
        return None

    async def _find_by_title(self, title: str, db: AsyncSession) -> Paper | None:
        from sqlalchemy import func
        r = await db.execute(
            select(Paper).where(func.lower(Paper.title) == title.lower().strip())
        )
        return r.scalar_one_or_none()

    @staticmethod
    def _parse_json(raw: str, context: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(f"paper_service.{context}.parse_error", error=str(exc))
            raise ValueError(f"Gemini returned invalid JSON for {context}: {exc}") from exc


# Module-level singleton
paper_service = PaperService()
