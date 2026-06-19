"""
app/schemas/chat.py
────────────────────
Pydantic schemas for Phase 5 — Paper Chat with Citations.
"""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    paper_id: str = Field(..., description="UUID of the uploaded/indexed paper")
    question: str = Field(..., min_length=2, max_length=1000)
    conversation_history: list[ChatMessage] = Field(
        default=[],
        description="Previous messages for multi-turn conversation",
    )


class Citation(BaseModel):
    chunk_index: int
    page: int | None = None
    text_snippet: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    paper_id: str
    question: str
