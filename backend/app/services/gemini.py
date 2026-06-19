"""
app/services/gemini.py
───────────────────────
Thin async wrapper around the Google Generative AI SDK.

Centralises model initialisation, prompt execution, and error handling
so every other service just calls `gemini_service.generate(prompt)`.

SDK docs: https://ai.google.dev/gemini-api/docs/get-started/python
"""

from __future__ import annotations

import asyncio

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiService:
    """
    Async interface to the Google Gemini API.

    The google-generativeai SDK is synchronous, so we run calls in a
    thread pool (asyncio.to_thread) to avoid blocking the FastAPI event loop.
    """

    def __init__(self) -> None:
        if not settings.gemini_api_key or settings.gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
            logger.warning(
                "gemini.no_api_key",
                msg=(
                    "GEMINI_API_KEY is not set or still the placeholder value. "
                    "All Gemini-powered endpoints (roadmap, summarise, explain, "
                    "chat, etc.) will fail until you set a real key in backend/.env "
                    "and restart the server."
                ),
            )

        genai.configure(api_key=settings.gemini_api_key)

        self._model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            generation_config=GenerationConfig(
                temperature=0.3,          # Lower = more deterministic / factual
                top_p=0.95,
                max_output_tokens=8192,
            ),
        )

        self._model_name = settings.gemini_model

    # ── Public API ─────────────────────────────────────────────────────────────

    async def generate(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the text response.

        Raises:
            GeminiError: On API failure after retries.
        """
        logger.debug("gemini.generate", prompt_length=len(prompt))

        response = await asyncio.to_thread(self._model.generate_content, prompt)

        text = response.text.strip()
        logger.debug("gemini.generate.done", response_length=len(text))
        return text

    async def generate_json(self, prompt: str) -> str:
        """
        Like generate() but instructs the model to return valid JSON only.
        Strips markdown code fences if the model wraps the JSON in them.
        """
        json_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Respond ONLY with valid JSON. "
            "Do not include markdown code fences, preamble, or explanation."
        )
        raw = await self.generate(json_prompt)
        # Strip ```json ... ``` if present
        return self._strip_code_fences(raw)

    @property
    def model_name(self) -> str:
        return self._model_name

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove markdown JSON code fences that some LLMs add."""
        text = text.strip()
        if text.startswith("```"):
            # Remove opening fence (```json or ```)
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return text.strip()


# Module-level singleton
gemini_service = GeminiService()
