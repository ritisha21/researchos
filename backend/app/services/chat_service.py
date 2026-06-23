"""
app/services/chat_service.py
─────────────────────────────
Phase 5 — RAG-based chat with citations.

ChromaDB ownership boundary: every query is filtered by paper_id using
ChromaDB's `where` clause, so a user can never retrieve vectors from
another paper — even if they know or guess a valid paper_id.
The paper_id is validated against PostgreSQL (exists + is_indexed) in
the route layer BEFORE this service is called, ensuring the chain is:

  Route: paper exists in PG AND is_indexed
    → Service: query ChromaDB WHERE paper_id = <validated_id>
      → No cross-paper data leakage possible
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

You have been given relevant excerpts from the paper, numbered [1], [2], [3] etc.
Use ONLY these excerpts to answer the question. Cite inline using [N] notation.
If the excerpts don't contain enough to answer, say so clearly.
Be precise, technical, and concise.

--- PAPER EXCERPTS ---
{context}
--- END EXCERPTS ---

{history_block}
"""


class ChatService:

    async def chat(self, request: ChatRequest) -> ChatResponse:
        # Query ChromaDB — hard-filtered to this paper's vectors only.
        # The `where={"paper_id": request.paper_id}` clause in pdf_service.query_paper
        # is the ownership boundary — other papers' chunks are structurally unreachable.
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

        # Build context block
        context_lines = []
        for i, chunk in enumerate(chunks, start=1):
            page_info = f" (page {chunk['page']})" if chunk.get("page") else ""
            context_lines.append(f"[{i}]{page_info}\n{chunk['text']}")
        context_block = "\n\n".join(context_lines)

        # Build conversation history block (last 6 turns only)
        history_block = ""
        if request.conversation_history:
            lines = []
            for msg in request.conversation_history[-6:]:
                role = "User" if msg.role == "user" else "Assistant"
                lines.append(f"{role}: {msg.content}")
            history_block = "--- PREVIOUS CONVERSATION ---\n" + "\n".join(lines) + "\n--- END ---\n"

        system = CHAT_SYSTEM_PROMPT.format(context=context_block, history_block=history_block)
        full_prompt = f"{system}\nUser question: {request.question}\n\nAnswer:"

        logger.info("chat_service.generating", paper_id=request.paper_id)
        answer = await gemini_service.generate(full_prompt)
        citations = self._extract_citations(answer, chunks)

        return ChatResponse(
            answer=answer,
            citations=citations,
            paper_id=request.paper_id,
            question=request.question,
        )

    @staticmethod
    def _extract_citations(answer: str, chunks: list[dict]) -> list[Citation]:
        cited = set(int(m) for m in re.findall(r"\[(\d+)\]", answer))
        citations = []
        for ref_num in sorted(cited):
            idx = ref_num - 1
            if 0 <= idx < len(chunks):
                chunk = chunks[idx]
                snippet = chunk["text"][:200].strip()
                if len(chunk["text"]) > 200:
                    snippet += "..."
                citations.append(Citation(
                    chunk_index=chunk.get("chunk_index", idx),
                    page=chunk.get("page"),
                    text_snippet=snippet,
                    relevance_score=chunk.get("score", 0.0),
                ))
        return citations


chat_service = ChatService()
