"""
app/services/roadmap_service.py
────────────────────────────────
Orchestrates roadmap generation:

  1. Check PostgreSQL cache (topic lookup)
  2. If miss → call Gemini with a structured prompt
  3. Parse the JSON response into validated Pydantic schemas
  4. Persist to PostgreSQL for future cache hits
  5. Return the RoadmapResponse

Design notes
────────────
- The topic key is normalised to lowercase + stripped for reliable cache hits.
- force_refresh=True bypasses cache and overwrites the stored record.
- If Gemini returns malformed JSON we log the error and raise so the caller
  can return a meaningful HTTP 502 rather than a 500.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.roadmap import Roadmap
from app.schemas.roadmap import (
    LearningStep,
    PaperReference,
    RoadmapRequest,
    RoadmapResponse,
)
from app.services.gemini import gemini_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Prompt template ────────────────────────────────────────────────────────────
ROADMAP_PROMPT = """\
You are an expert AI research mentor.

Generate a comprehensive, structured research learning roadmap for the topic:
"{topic}"

Return ONLY a valid JSON object with EXACTLY these keys:

{{
  "prerequisites": [
    "string describing a required background skill or concept"
  ],
  "learning_path": [
    {{
      "order": 1,
      "topic": "Short topic name",
      "description": "One-sentence description of what to learn",
      "estimated_hours": 10
    }}
  ],
  "foundational_papers": [
    {{
      "title": "Paper title",
      "authors": ["Author Name"],
      "year": 2015,
      "url": "https://arxiv.org/abs/...",
      "why_important": "One sentence explaining importance"
    }}
  ],
  "intermediate_papers": [ {{ same structure as foundational_papers }} ],
  "advanced_papers": [ {{ same structure as foundational_papers }} ],
  "research_frontiers": [
    "string describing a current active research direction"
  ],
  "research_gaps": [
    "string describing an open problem or gap in the literature"
  ],
  "recommended_reading_order": [
    "Paper title or concept in the order a learner should encounter them"
  ]
}}

Rules:
- prerequisites: 4–8 items (background math, ML, programming)
- learning_path: 5–8 ordered steps
- foundational_papers: 3–5 seminal papers every researcher must read
- intermediate_papers: 3–5 papers for practitioners with some background
- advanced_papers: 3–5 cutting-edge or highly technical papers
- research_frontiers: 4–6 active research directions (present tense)
- research_gaps: 4–6 unsolved problems or open questions
- recommended_reading_order: 8–15 titles / concepts in chronological learning order
- Use real, verifiable paper titles and authors.
- Provide arXiv or DOI URLs where known; use null if unknown.
- All text must be in English.
"""


class RoadmapService:
    """Generates and caches research learning roadmaps."""

    # ── Public API ─────────────────────────────────────────────────────────────

    async def generate_roadmap(
        self,
        request: RoadmapRequest,
        db: AsyncSession,
    ) -> RoadmapResponse:
        """
        Main entry point.  Returns a cached or freshly generated roadmap.
        """
        topic_key = request.topic.lower().strip()

        # ── 1. Cache lookup ────────────────────────────────────────────────────
        if not request.force_refresh:
            cached = await self._fetch_from_cache(topic_key, db)
            if cached:
                logger.info("roadmap.cache_hit", topic=topic_key)
                return self._to_response(cached, cached=True)

        # ── 2. Generate via Gemini ─────────────────────────────────────────────
        logger.info("roadmap.generating", topic=request.topic)
        raw_json = await self._call_llm(request.topic)

        # ── 3. Parse & validate ────────────────────────────────────────────────
        parsed = self._parse_llm_response(raw_json)

        # ── 4. Persist ─────────────────────────────────────────────────────────
        roadmap_record = await self._upsert(
            topic_key=topic_key,
            topic_display=request.topic,
            parsed=parsed,
            raw=raw_json,
            db=db,
        )

        logger.info("roadmap.generated", topic=topic_key, id=str(roadmap_record.id))
        return self._to_response(roadmap_record, cached=False)

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _fetch_from_cache(
        self, topic_key: str, db: AsyncSession
    ) -> Roadmap | None:
        result = await db.execute(
            select(Roadmap).where(Roadmap.topic == topic_key)
        )
        return result.scalar_one_or_none()

    async def _call_llm(self, topic: str) -> str:
        prompt = ROADMAP_PROMPT.format(topic=topic)
        return await gemini_service.generate_json(prompt)

    def _parse_llm_response(self, raw_json: str) -> dict:
        """Parse LLM JSON output and validate required keys."""
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.error("roadmap.parse_error", error=str(exc), raw=raw_json[:500])
            raise ValueError(f"Gemini returned invalid JSON: {exc}") from exc

        required_keys = {
            "prerequisites",
            "learning_path",
            "foundational_papers",
            "intermediate_papers",
            "advanced_papers",
            "research_frontiers",
            "research_gaps",
            "recommended_reading_order",
        }
        missing = required_keys - set(data.keys())
        if missing:
            logger.error("roadmap.missing_keys", missing=missing)
            raise ValueError(f"Gemini response missing required keys: {missing}")

        return data

    async def _upsert(
        self,
        topic_key: str,
        topic_display: str,
        parsed: dict,
        raw: str,
        db: AsyncSession,
    ) -> Roadmap:
        """Insert a new roadmap or update an existing one (force_refresh path)."""
        existing = await db.execute(
            select(Roadmap).where(Roadmap.topic == topic_key)
        )
        record = existing.scalar_one_or_none()

        if record is None:
            record = Roadmap(id=uuid.uuid4(), topic=topic_key, topic_display=topic_display)
            db.add(record)

        record.topic_display = topic_display
        record.prerequisites = parsed.get("prerequisites", [])
        record.learning_path = parsed.get("learning_path", [])
        record.foundational_papers = parsed.get("foundational_papers", [])
        record.intermediate_papers = parsed.get("intermediate_papers", [])
        record.advanced_papers = parsed.get("advanced_papers", [])
        record.research_frontiers = parsed.get("research_frontiers", [])
        record.research_gaps = parsed.get("research_gaps", [])
        record.recommended_reading_order = parsed.get("recommended_reading_order", [])
        record.generated_by_model = gemini_service.model_name
        record.raw_llm_response = raw

        await db.flush()   # Write to DB, session commit handled by get_db dependency
        await db.refresh(record)
        return record

    @staticmethod
    def _to_response(record: Roadmap, *, cached: bool) -> RoadmapResponse:
        """Convert a Roadmap ORM record into the API response schema."""

        def _coerce_papers(raw_list: list) -> list[PaperReference]:
            out = []
            for item in raw_list:
                if isinstance(item, dict):
                    out.append(PaperReference(**{k: v for k, v in item.items() if k in PaperReference.model_fields}))
                elif isinstance(item, str):
                    out.append(PaperReference(title=item))
            return out

        def _coerce_steps(raw_list: list) -> list[LearningStep]:
            out = []
            for i, item in enumerate(raw_list, start=1):
                if isinstance(item, dict):
                    out.append(LearningStep(
                        order=item.get("order", i),
                        topic=item.get("topic", ""),
                        description=item.get("description", ""),
                        estimated_hours=item.get("estimated_hours"),
                    ))
                elif isinstance(item, str):
                    out.append(LearningStep(order=i, topic=item, description=""))
            return out

        return RoadmapResponse(
            id=record.id,
            topic=record.topic,
            topic_display=record.topic_display,
            prerequisites=record.prerequisites or [],
            learning_path=_coerce_steps(record.learning_path or []),
            foundational_papers=_coerce_papers(record.foundational_papers or []),
            intermediate_papers=_coerce_papers(record.intermediate_papers or []),
            advanced_papers=_coerce_papers(record.advanced_papers or []),
            research_frontiers=record.research_frontiers or [],
            research_gaps=record.research_gaps or [],
            recommended_reading_order=record.recommended_reading_order or [],
            generated_by_model=record.generated_by_model,
            cached=cached,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


# Module-level singleton
roadmap_service = RoadmapService()
