# DevDocs AI

A production-ready RAG (Retrieval-Augmented Generation) assistant that lets you ask natural language questions about any codebase. Point it at a GitHub repo or upload files, and get accurate answers with source citations — in real time.

**Live Demo:** [devdocs-ai-beryl.vercel.app](https://devdocs-ai-beryl.vercel.app)

---

## What It Does

- **Index any GitHub repo** via URL (shallow clone, no auth needed for public repos)
- **Upload files or ZIP archives** for local codebases
- **Ask questions in plain English** — "How does authentication work?" / "Where is rate limiting implemented?"
- **Get streaming answers** with source citations (file path + line numbers)
- **Multi-collection support** — each indexed repo is stored separately, switch between them

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript, Vite, TailwindCSS |
| Backend | FastAPI (Python 3.11), WebSocket streaming |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Embeddings | HuggingFace Inference API — `all-MiniLM-L6-v2` (384-dim) |
| Vector DB | Qdrant Cloud (cosine similarity) |
| Cache | Upstash Redis (serverless HTTP) |
| Deployment | Railway (backend) + Vercel (frontend) |

---

## Architecture

```
Browser
  │
  ├── HTTP/REST ──► FastAPI (Railway)
  └── WebSocket ──► FastAPI (Railway)
                        │
            ┌───────────┼───────────────┐
            ▼           ▼               ▼
        Qdrant       Groq API      Upstash Redis
        Cloud        (LLM)         (Cache)
            │
    HuggingFace API
    (Embeddings)
```

**Request flow:**
1. User submits a question via WebSocket
2. Backend generates a query embedding (HuggingFace API, cached in Redis)
3. Qdrant returns the top-5 most relevant code chunks
4. Backend streams the LLM response token-by-token (Groq) back over WebSocket
5. Frontend displays the answer live with source citations

**Ingestion flow:**
1. GitHub URL → shallow clone (`depth=1`) → extract supported files
2. AST-based chunking (Python/JS/TS/Markdown) or character chunking fallback
3. Parallel batch embedding (3 concurrent batches of 5 via HuggingFace API)
4. Store vectors + metadata in Qdrant Cloud

---

## Supported Languages

`.py` `.js` `.ts` `.tsx` `.jsx` `.java` `.go` `.cpp` `.c` `.h` `.rs` `.cu` `.cuh` `.cs` `.rb` `.swift` `.kt` `.scala` `.r` `.m` `.sh` `.yaml` `.yml` `.json` `.toml` `.sql` `.md`

Smart (AST-aware) chunking for Python, JavaScript/TypeScript, and Markdown. Character-based chunking with overlap for all other languages.

---

## Running Locally

### Prerequisites

You'll need free-tier accounts at:
- [Groq](https://console.groq.com) — LLM inference
- [HuggingFace](https://huggingface.co/settings/tokens) — embeddings
- [Qdrant Cloud](https://cloud.qdrant.io) — vector storage
- [Upstash](https://console.upstash.com) — Redis cache

### Backend

```bash
cd backend

python3.11 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Fill in your API keys in .env

uvicorn app.main:app --reload
# API running at http://localhost:8000
```

### Frontend

```bash
cd frontend

npm install

# Create frontend/.env
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env
echo "VITE_WS_URL=ws://localhost:8000/api/v1/stream" >> .env

npm run dev
# App running at http://localhost:5173
```

---

## Environment Variables

### Backend (`backend/.env`)

```bash
# Groq LLM
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile

# HuggingFace Embeddings
HF_API_KEY=your_hf_token
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Qdrant Cloud
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key

# Upstash Redis
UPSTASH_REDIS_REST_URL=https://your-instance.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_upstash_token

# Optional
ENABLE_CACHING=true
ENABLE_SMART_CHUNKING=true
RETRIEVAL_TOP_K=5
```

### Frontend (`frontend/.env`)

```bash
VITE_API_BASE_URL=https://your-backend.railway.app/api/v1
VITE_WS_URL=wss://your-backend.railway.app/api/v1/stream
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Service health + cache stats |
| `POST` | `/api/v1/ingest` | Upload files for indexing |
| `POST` | `/api/v1/ingest/github` | Index a GitHub repo by URL |
| `POST` | `/api/v1/query` | REST query (non-streaming) |
| `WS` | `/api/v1/stream` | WebSocket streaming chat |
| `GET` | `/api/v1/collections` | List indexed collections |
| `GET` | `/api/v1/stats` | System statistics |
| `GET` | `/api/v1/metrics` | Prometheus metrics |

---

## Key Implementation Details

**Parallel embedding** — batches of 5 texts sent to HuggingFace API, up to 3 batches in parallel using `asyncio.gather` + semaphore, with 0.5s delay between groups to respect rate limits.

**AST chunking** — Python files parsed with the `ast` module to extract complete functions and classes. JS/TS uses regex-based detection. Markdown splits by header hierarchy. All preserve full logical units for better retrieval.

**Caching** — embeddings cached in Upstash Redis for 24h using SHA256 hash of text as key. Query responses cached for 1h. System degrades gracefully if Redis is unavailable.

**Multi-collection** — each GitHub repo is indexed into its own Qdrant collection (named after the repo). The frontend tracks the active collection and routes queries to the correct one.

**WebSocket streaming** — Groq streaming API sends tokens as they're generated. Backend forwards each token to the browser over WebSocket, giving a typewriter effect with no perceived latency.

---

## Deployment

The project is deployed as two independent services:

- **Backend** on Railway — Dockerfile (`python:3.11-slim`), auto-deployed from `backend/` directory
- **Frontend** on Vercel — static build from `frontend/`, `VITE_API_BASE_URL` and `VITE_WS_URL` set as environment variables

No Docker Compose or local infrastructure required — all dependencies (Qdrant, Redis, LLM) are managed cloud services.

---

## Project Structure

```
devdocs-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py        # REST endpoints
│   │   │   └── websocket.py     # WebSocket streaming
│   │   ├── services/
│   │   │   ├── cache.py         # Upstash Redis caching
│   │   │   ├── embeddings.py    # HuggingFace embedding + batching
│   │   │   ├── ingestion.py     # GitHub clone + file processing
│   │   │   ├── llm.py           # Groq LLM integration
│   │   │   ├── metrics.py       # Prometheus metrics (15+ counters)
│   │   │   └── retrieval.py     # Qdrant vector search
│   │   ├── utils/
│   │   │   ├── ast_chunking.py  # Language-aware chunking
│   │   │   ├── chunking.py      # Character-based fallback
│   │   │   └── parsing.py       # File parsing + language detection
│   │   ├── config.py            # Pydantic settings
│   │   ├── main.py              # FastAPI app
│   │   └── models.py            # Request/response models
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ChatInterface.tsx
    │   │   ├── MessageList.tsx
    │   │   ├── MessageInput.tsx
    │   │   ├── SourceCitation.tsx
    │   │   ├── UploadPanel.tsx
    │   │   └── CodeBlock.tsx
    │   ├── hooks/
    │   │   ├── useWebSocket.ts
    │   │   └── useChat.ts
    │   ├── services/api.ts
    │   ├── types/index.ts
    │   └── App.tsx
    ├── package.json
    └── vite.config.ts
```
