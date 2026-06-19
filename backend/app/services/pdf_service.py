"""
app/services/pdf_service.py
────────────────────────────
Phase 4 — PDF Upload Pipeline

Flow:
  PDF file → extract text (pypdf + pdfplumber fallback)
           → chunk into overlapping segments
           → embed via Gemini embedding model
           → store vectors in ChromaDB
           → update Paper record (has_pdf=True, is_indexed=True)

Design notes
────────────
- pypdf handles clean digital PDFs fast.
- pdfplumber is used as fallback for complex layouts (tables, multi-column).
- Chunks overlap by CHUNK_OVERLAP tokens to preserve context across boundaries.
- Each chunk is stored in ChromaDB with metadata: paper_id, chunk_index, page.
- Embedding runs in a thread pool (Gemini SDK is synchronous).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import chromadb
import pypdf
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 150     # overlap between consecutive chunks


def _get_chroma_client() -> chromadb.ClientAPI:
    """Return a persistent ChromaDB client."""
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _get_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


class PDFService:
    """Handles PDF extraction, chunking, embedding, and ChromaDB storage."""

    # ── Public API ─────────────────────────────────────────────────────────────

    async def process_pdf(
        self,
        file_bytes: bytes,
        paper_id: str,
        filename: str,
    ) -> dict:
        """
        Full pipeline: save → extract → chunk → embed → store.

        Returns:
            {"paper_id": ..., "chunks": n, "saved_path": ...}
        """
        # 1. Save file to disk
        saved_path = await self._save_file(file_bytes, paper_id, filename)

        # 2. Extract text
        text, page_map = await asyncio.to_thread(self._extract_text, saved_path)
        if not text.strip():
            raise ValueError("Could not extract text from PDF. File may be scanned/image-only.")

        # 3. Chunk
        chunks = self._chunk_text(text, page_map)
        logger.info("pdf_service.chunked", paper_id=paper_id, chunks=len(chunks))

        # 4. Embed + store in ChromaDB
        await asyncio.to_thread(self._embed_and_store, chunks, paper_id)

        return {
            "paper_id": paper_id,
            "chunks": len(chunks),
            "saved_path": str(saved_path),
        }

    async def delete_paper_vectors(self, paper_id: str) -> None:
        """Remove all ChromaDB vectors for a paper (used on paper deletion)."""
        await asyncio.to_thread(self._delete_vectors, paper_id)

    async def query_paper(
        self,
        paper_id: str,
        question: str,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Retrieve the top-n most relevant chunks for a question.

        Returns list of dicts with keys: text, chunk_index, page, score.
        """
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)

        embedding = await asyncio.to_thread(
            lambda: genai.embed_content(
                model=settings.gemini_embedding_model,
                content=question,
                task_type="retrieval_query",
            )["embedding"]
        )

        client = _get_chroma_client()
        collection = _get_collection(client)

        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where={"paper_id": paper_id},
        )

        chunks = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                score = results["distances"][0][i] if results["distances"] else 0.0
                chunks.append({
                    "text": doc,
                    "chunk_index": meta.get("chunk_index", i),
                    "page": meta.get("page"),
                    "score": round(1 - score, 4),   # cosine: distance → similarity
                })
        return chunks

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _save_file(
        self, file_bytes: bytes, paper_id: str, filename: str
    ) -> Path:
        upload_dir = Path(settings.upload_dir) / paper_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest = upload_dir / filename
        await asyncio.to_thread(dest.write_bytes, file_bytes)
        logger.info("pdf_service.saved", path=str(dest))
        return dest

    @staticmethod
    def _extract_text(path: Path) -> tuple[str, dict[int, int]]:
        """
        Extract full text from PDF.
        Returns (full_text, page_map) where page_map[char_offset] = page_number.
        """
        full_text = ""
        page_map: dict[int, int] = {}   # char_start_offset → page number

        try:
            reader = pypdf.PdfReader(str(path))
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                page_map[len(full_text)] = page_num
                full_text += page_text + "\n"
        except Exception as exc:
            logger.warning("pdf_service.pypdf_failed", error=str(exc))
            # Fallback to pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(str(path)) as pdf:
                    full_text = ""
                    page_map = {}
                    for page_num, page in enumerate(pdf.pages, start=1):
                        page_text = page.extract_text() or ""
                        page_map[len(full_text)] = page_num
                        full_text += page_text + "\n"
            except Exception as exc2:
                logger.error("pdf_service.pdfplumber_failed", error=str(exc2))
                raise

        return full_text, page_map

    @staticmethod
    def _chunk_text(
        text: str, page_map: dict[int, int]
    ) -> list[dict]:
        """Split text into overlapping chunks with page metadata."""
        chunks = []
        start = 0
        chunk_index = 0
        page_offsets = sorted(page_map.keys())

        def _get_page(offset: int) -> int:
            page = 1
            for po in page_offsets:
                if po <= offset:
                    page = page_map[po]
                else:
                    break
            return page

        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "page": _get_page(start),
                })
                chunk_index += 1
            start += CHUNK_SIZE - CHUNK_OVERLAP

        return chunks

    @staticmethod
    def _embed_and_store(chunks: list[dict], paper_id: str) -> None:
        """Generate embeddings and store in ChromaDB."""
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)

        client = _get_chroma_client()
        collection = _get_collection(client)

        # Delete any existing vectors for this paper (re-upload case)
        try:
            collection.delete(where={"paper_id": paper_id})
        except Exception:
            pass

        batch_size = 50   # Embed in batches to avoid API limits
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]

            embeddings_result = genai.embed_content(
                model=settings.gemini_embedding_model,
                content=texts,
                task_type="retrieval_document",
            )
            embeddings = embeddings_result["embedding"]

            ids = [f"{paper_id}_chunk_{c['chunk_index']}" for c in batch]
            metadatas = [
                {"paper_id": paper_id, "chunk_index": c["chunk_index"], "page": c["page"] or 0}
                for c in batch
            ]

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

        logger.info("pdf_service.embedded", paper_id=paper_id, total_chunks=len(chunks))

    @staticmethod
    def _delete_vectors(paper_id: str) -> None:
        client = _get_chroma_client()
        collection = _get_collection(client)
        try:
            collection.delete(where={"paper_id": paper_id})
            logger.info("pdf_service.vectors_deleted", paper_id=paper_id)
        except Exception as exc:
            logger.warning("pdf_service.delete_failed", paper_id=paper_id, error=str(exc))


# Module-level singleton
pdf_service = PDFService()
