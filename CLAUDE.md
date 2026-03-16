# DevDocs AI — Developer Notes

## Current Stack (Cloud-Hosted)

| Component | Service | Details |
|-----------|---------|---------|
| LLM | Groq API | `llama-3.3-70b-versatile` |
| Embeddings | HuggingFace Inference API | `all-MiniLM-L6-v2`, 384-dim |
| Vector DB | Qdrant Cloud | Cosine distance, payload index on `file_path` |
| Cache | Upstash Redis | Serverless HTTP (upstash-py) |
| Backend Deploy | Railway | Dockerfile, python:3.11-slim |
| Frontend Deploy | Vercel | Static build, env vars via dashboard |

## Live URLs

- Frontend: `https://devdocs-ai-beryl.vercel.app`
- Backend: `https://web-production-26ffd.up.railway.app`

## Architecture Notes

### Embedding Service (`backend/app/services/embeddings.py`)
- Calls HuggingFace Inference API (not local SentenceTransformers)
- Batches of 5 texts, 3 concurrent batches via `asyncio.gather` + semaphore
- 0.5s delay between groups to avoid rate limits
- Exponential backoff retry on 429/503 (up to 5 attempts)
- Results cached in Upstash Redis (SHA256 hash key, 24h TTL)

### Retrieval Service (`backend/app/services/retrieval.py`)
- Uses `qdrant-client` — `query_points()` (not deprecated `search()`)
- Creates keyword payload index on `file_path` at collection creation (required for filter queries)
- `delete_by_file_path` handles "collection doesn't exist" gracefully (returns 0 on first run)
- Each GitHub repo gets its own Qdrant collection

### LLM Service (`backend/app/services/llm.py`)
- Groq streaming API via httpx
- Tokens forwarded over WebSocket as they arrive

### Ingestion (`backend/app/services/ingestion.py`)
- GitHub: shallow clone `depth=1` via gitpython
- AST chunking for Python (ast module), JS/TS (regex), Markdown (headers)
- Character-based chunking fallback for all other languages
- Supported extensions: `.py,.js,.ts,.java,.go,.md,.tsx,.jsx,.cpp,.c,.h,.rs,.cu,.cuh,.cs,.rb,.swift,.kt,.scala,.r,.m,.sh,.yaml,.yml,.json,.toml,.sql`

### Cache Service (`backend/app/services/cache.py`)
- Upstash Redis via REST HTTP (not standard redis-py)
- Embedding cache: 24h TTL
- Response cache: 1h TTL
- Graceful degradation — system works if Redis is down

### Frontend (`frontend/src/`)
- WebSocket URL: `import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/stream'`
- `activeCollection` tracked in ChatInterface state, sent with every WebSocket message
- UploadPanel: GitHub tab is default
- SourceCitation strips `/tmp/xxx/repo/` prefix from displayed file paths

## Deployment

### Railway (Backend)
- Root `railway.json` points to `backend/` as build context
- `startCommand` removed — CMD in Dockerfile handles port: `sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"`
- All env vars set via Railway dashboard Variables tab
- Do NOT commit a root-level `Procfile` — it breaks Railway's build detection

### Vercel (Frontend)
- Build command: `npm run build`
- Output directory: `dist`
- Env vars: `VITE_API_BASE_URL` and `VITE_WS_URL` set in Vercel dashboard

## Services Needed to Keep the Project Live

Everything is cloud-hosted. No local infrastructure required. All services have free tiers.

### 1. Railway — Backend Hosting
- URL: https://railway.app
- What it runs: FastAPI backend (Dockerfile)
- Repo connected: `arshadvani3/devdocs-ai`, root directory `backend/`
- Live URL: `https://web-production-26ffd.up.railway.app`
- **If it goes down:** redeploy from Railway dashboard → Deployments → Redeploy

### 2. Vercel — Frontend Hosting
- URL: https://vercel.com
- What it runs: React 19 + TypeScript static build
- Repo connected: same GitHub repo, `frontend/` directory
- Live URL: `https://devdocs-ai-beryl.vercel.app`
- **If it goes down:** auto-redeploys on every push to main

### 3. Groq — LLM Inference
- URL: https://console.groq.com
- What it does: runs `llama-3.3-70b-versatile`, streams tokens to backend
- Key name in Railway env vars: `GROQ_API_KEY`
- Free tier: generous daily token limit, no credit card needed

### 4. HuggingFace — Embeddings
- URL: https://huggingface.co/settings/tokens
- What it does: converts text chunks to 384-dim vectors via Inference API
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Key name in Railway env vars: `HF_API_KEY`
- Free tier: rate limited (handled by retry logic in embeddings.py)

### 5. Qdrant Cloud — Vector Database
- URL: https://cloud.qdrant.io
- What it does: stores and searches all code chunk embeddings
- Key names in Railway env vars: `QDRANT_URL`, `QDRANT_API_KEY`
- Free tier: 1 cluster, 1GB storage
- **Note:** each indexed GitHub repo creates its own collection here

### 6. Upstash — Redis Cache
- URL: https://console.upstash.com
- What it does: caches embeddings (24h) and query responses (1h)
- Key names in Railway env vars: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`
- Free tier: 10,000 requests/day
- **Note:** system works fine without it (graceful degradation)

---

### All Railway Environment Variables (Backend)

```
GROQ_API_KEY
GROQ_MODEL=llama-3.3-70b-versatile
HF_API_KEY
EMBEDDING_MODEL=all-MiniLM-L6-v2
QDRANT_URL
QDRANT_API_KEY
QDRANT_COLLECTION_NAME=devdocs
UPSTASH_REDIS_REST_URL
UPSTASH_REDIS_REST_TOKEN
ENABLE_CACHING=true
ENABLE_SMART_CHUNKING=true
CORS_ORIGINS=https://devdocs-ai-beryl.vercel.app
```

### All Vercel Environment Variables (Frontend)

```
VITE_API_BASE_URL=https://web-production-26ffd.up.railway.app/api/v1
VITE_WS_URL=wss://web-production-26ffd.up.railway.app/api/v1/stream
```

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `QdrantClient has no attribute 'search'` | Use `query_points()`, returns `response.points` |
| Qdrant 400 on filter query | Create keyword payload index on `file_path` at collection creation |
| Qdrant 404 on first ingestion | `delete_by_file_path` must handle "collection doesn't exist" gracefully |
| AI answering from wrong collection | Send `collection_name` in WebSocket message from ChatInterface |
| Railway `$PORT` literal | Don't pass `$PORT` as string in `startCommand`; use Dockerfile CMD with shell form |
| WebSocket connects to localhost | Use `VITE_WS_URL` env var, never hardcode |
