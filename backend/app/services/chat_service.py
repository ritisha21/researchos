"""
app/services/chat_service.py
─────────────────────────────
Phase 5 — Paper Chat with Citations

Pipeline:
  User question
    → embed question
    → retrieve top-k chunks from ChromaDB (filtered by paper_id)
    → build context-aware prompt with retrieved chunks
    → call Gemini with conversation history
    → parse answer + extract citation references
    → return ChatResponse with answer + citations

Design notes
────────────
- The system prompt instructs Gemini to cite chunks by index [1], [2], etc.
- Citations are parsed from the response and matched back to retrieved chunks.
- Conversation history is included so users can ask follow-up questions.
- If no relevant chunks are found, Gemini answers from general knowledge
  but is told to flag this clearly.
"""

from __future__ import annotations

import re

from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, Citation
from app.services.gemini import gemini_service
from app.services.pdf_service import pdf_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

CHAT_SYSTEM_PROMPT = """\
You are an expert research assistant helping a user understand a research paper.

You have been given relevant excerpts from the paper below, numbered as [1], [2], [3], etc.
Use ONLY these excerpts to answer the question. When you use information from an excerpt,
cite it inline using its number like [1] or [2].

If the excerpts do not contain enough information to answer the question, say so clearly
and indicate that the answer may be outside the provided sections.

Be precise, technical, and helpful. Use clear language.

--- PAPER EXCERPTS ---
{context}
--- END EXCERPTS ---

{history_block}
"""


class ChatService:
    """Orchestrates RAG-based chat over an uploaded paper."""

    async def chat(self, request: ChatRequest) -> ChatResponse:
        # 1. Retrieve relevant chunks from ChromaDB
        chunks = await pdf_service.query_paper(
            paper_id=request.paper_id,
            question=request.question,
            n_results=6,
        )

        if not chunks:
            logger.warning("chat_service.no_chunks", paper_id=request.paper_id)
            return ChatResponse(
                answer=(
                    "I couldn't find relevant sections in this paper to answer your question. "
                    "The paper may not have been indexed yet, or the question may be outside its scope."
                ),
                citations=[],
                paper_id=request.paper_id,
                question=request.question,
            )

        # 2. Build context block
        context_lines = []
        for i, chunk in enumerate(chunks, start=1):
            page_info = f" (page {chunk['page']})" if chunk.get("page") else ""
            context_lines.append(f"[{i}]{page_info}\n{chunk['text']}")
        context_block = "\n\n".join(context_lines)

        # 3. Build conversation history block
        history_block = ""
        if request.conversation_history:
            history_lines = []
            for msg in request.conversation_history[-6:]:   # last 6 turns
                role = "User" if msg.role == "user" else "Assistant"
                history_lines.append(f"{role}: {msg.content}")
            history_block = "--- PREVIOUS CONVERSATION ---\n" + "\n".join(history_lines) + "\n--- END CONVERSATION ---\n"

        # 4. Build final prompt
        system = CHAT_SYSTEM_PROMPT.format(
            context=context_block,
            history_block=history_block,
        )
        full_prompt = f"{system}\nUser question: {request.question}\n\nAnswer:"

        # 5. Call Gemini
        logger.info("chat_service.generating", paper_id=request.paper_id)
        answer = await gemini_service.generate(full_prompt)

        # 6. Extract citations from answer text
        citations = self._extract_citations(answer, chunks)

        return ChatResponse(
            answer=answer,
            citations=citations,
            paper_id=request.paper_id,
            question=request.question,
        )

    # ── Private ────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_citations(answer: str, chunks: list[dict]) -> list[Citation]:
        """
        Parse [1], [2] style references from the answer and match to chunks.
        """
        cited_indices = set(int(m) for m in re.findall(r"\[(\d+)\]", answer))
        citations = []

        for ref_num in sorted(cited_indices):
            chunk_idx = ref_num - 1   # answer uses 1-based, chunks list is 0-based
            if 0 <= chunk_idx < len(chunks):
                chunk = chunks[chunk_idx]
                snippet = chunk["text"][:200].strip()
                if len(chunk["text"]) > 200:
                    snippet += "..."
                citations.append(Citation(
                    chunk_index=chunk.get("chunk_index", chunk_idx),
                    page=chunk.get("page"),
                    text_snippet=snippet,
                    relevance_score=chunk.get("score", 0.0),
                ))

        return citations


# Module-level singleton
chat_service = ChatService()
