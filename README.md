# ResearchOS 🔬

> AI-powered research learning platform — Full MVP (Phases 1–5)

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.115 · Python 3.12 |
| Database | PostgreSQL 16 (async via asyncpg + SQLAlchemy 2) |
| Vector DB | ChromaDB 0.5 |
| AI | Google Gemini 1.5 Flash + text-embedding-004 |
| Paper APIs | Semantic Scholar Graph API · arXiv |
| Migrations | Alembic |
| Container | Docker + Docker Compose |

---

## Project Structure

```
researchos/
├── backend/
│   ├── app/
│   │   ├── main.py                      # App factory — all 5 phases wired
│   │   ├── config.py                    # Pydantic-Settings (.env loader)
│   │   ├── database/
│   │   │   ├── base.py                  # SQLAlchemy DeclarativeBase
│   │   │   └── session.py               # Async engine + get_db dependency
│   │   ├── models/
│   │   │   ├── paper.py                 # ORM: papers table
│   │   │   └── roadmap.py               # ORM: roadmaps table
│   │   ├── schemas/
│   │   │   ├── paper.py                 # Search, summarise, explain, notes, takeaways
│   │   │   ├── roadmap.py               # Roadmap request/response
│   │   │   └── chat.py                  # Chat request/response + Citation
│   │   ├── routes/
│   │   │   ├── health.py                # GET /health, /health/ready
│   │   │   ├── roadmap.py               # POST /api/v1/roadmap
│   │   │   ├── papers.py                # GET/POST /api/v1/papers/*
│   │   │   ├── upload.py                # POST /api/v1/upload
│   │   │   └── chat.py                  # POST /api/v1/chat
│   │   ├── services/
│   │   │   ├── gemini.py                # Gemini LLM wrapper
│   │   │   ├── semantic_scholar.py      # Semantic Scholar API client
│   │   │   ├── arxiv_service.py         # arXiv API client
│   │   │   ├── search_service.py        # Fan-out search + dedup + sort
│   │   │   ├── paper_service.py         # CRUD + AI analysis (Phase 3)
│   │   │   ├── roadmap_service.py       # Roadmap generation + caching
│   │   │   ├── pdf_service.py           # PDF extract + chunk + embed (Phase 4)
│   │   │   └── chat_service.py          # RAG chat with citations (Phase 5)
│   │   └── utils/
│   │       └── logger.py                # Structlog
│   ├── alembic/                         # DB migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env                             # Fill in your keys
│   └── .env.example
├── frontend/                            # Next.js 15 (future)
├── docker-compose.yml
├── .gitignore
└── POWERSHELL_COMMANDS.ps1              # Windows testing guide
```

---

## Quick Start

### 1. Get a Gemini API key
Free at: https://aistudio.google.com/apikey

### 2. Configure .env
```
cd backend
# Open .env and set GEMINI_API_KEY=your-key-here
```

### 3. Start with Docker
```bash
docker-compose up --build
```

### 4. Open Swagger UI
http://localhost:8000/docs

---

## API Reference

### Phase 1 — Research Navigator
```
POST /api/v1/roadmap
Body: { "topic": "Computer Vision" }
```

### Phase 2 — Paper Search
```
GET  /api/v1/papers/search?q=ResNet&limit=10
POST /api/v1/papers/search
Body: { "query": "...", "sources": ["semantic_scholar","arxiv"], "sort_by": "citation_count" }
GET  /api/v1/papers/{uuid}
```

### Phase 3 — Paper Analysis
```
POST /api/v1/papers/summarise        → summary + contributions + limitations + future work
POST /api/v1/papers/explain          → beginner-friendly explanation
POST /api/v1/papers/notes            → 8-12 structured study notes
POST /api/v1/papers/takeaways        → 5-8 practical takeaways
POST /api/v1/papers/literature-review → multi-paper literature review
```

### Phase 4 — PDF Upload
```
POST /api/v1/upload   (multipart/form-data)
Fields: file (PDF), title, authors, year, abstract
Returns: { paper_id, chunks_indexed, message }
```

### Phase 5 — Paper Chat
```
POST /api/v1/chat
Body: { "paper_id": "uuid", "question": "What are the contributions?", "conversation_history": [] }
Returns: { answer, citations: [{ chunk_index, page, text_snippet, relevance_score }] }
```

---

## Development (no Docker)

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL separately
docker run -d -e POSTGRES_USER=researchos -e POSTGRES_PASSWORD=researchos `
    -e POSTGRES_DB=researchos_db -p 5432:5432 postgres:16-alpine

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
