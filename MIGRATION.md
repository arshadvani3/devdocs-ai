# Migration Guide: Local Stack → Cloud Stack

This document describes what changed, why, and how to roll back if needed.

---

## What Changed and Why

### ChromaDB → Qdrant Cloud

| | Before | After |
|---|---|---|
| Package | `chromadb==0.4.18` | `qdrant-client>=1.7.0` |
| Hosting | Local Docker / on-disk | Qdrant Cloud (free 1GB cluster) |
| Config | `CHROMA_PERSIST_DIRECTORY`, `CHROMA_COLLECTION_NAME` | `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_NAME` |

**Why:** ChromaDB requires local disk persistence which doesn't work well on Railway's ephemeral filesystem. Qdrant Cloud is a managed service with a free tier that survives deploys.

**Key implementation changes in `retrieval.py`:**
- String chunk IDs converted to deterministic UUIDs via `uuid.uuid5()` (Qdrant requires UUID or int IDs)
- Vectors stored with full payload: `{chunk_id, code, file_path, start_line, end_line, language, chunk_type, chunk_index}`
- All Qdrant client calls are synchronous but wrapped in `asyncio.to_thread()` to avoid blocking the event loop
- Cosine similarity scores from Qdrant are already in `[0, 1]` for normalized vectors

---

### SentenceTransformers → HuggingFace Inference API

| | Before | After |
|---|---|---|
| Package | `sentence-transformers==2.2.2`, `torch==2.1.1` | `httpx>=0.27.0` (already present) |
| Hosting | Local CPU/GPU inference | HuggingFace Inference API (free tier) |
| Config | `EMBEDDING_DEVICE`, `EMBEDDING_BATCH_SIZE` | `HF_API_KEY` |

**Why:** `torch` + `sentence-transformers` is ~2GB of dependencies. Railway's free tier has build size limits and the model would need to re-download on every deploy. The HuggingFace Inference API hosts the exact same `all-MiniLM-L6-v2` model with no download required.

**Key implementation changes in `embeddings.py`:**
- HTTP POST to `https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2`
- Batches of 5 texts with 1s delay between batches (free tier rate limiting)
- Exponential backoff retry on 429 (rate limit) and 503 (model loading) errors
- `EMBEDDING_DIM` hardcoded to 384 (same model, same dimension)
- Cache integration preserved exactly — embeddings still cached in Upstash Redis

---

### Ollama → Groq API

| | Before | After |
|---|---|---|
| Package | None (HTTP via httpx) | `groq>=0.4.0` |
| Hosting | Local Ollama server | Groq Cloud API |
| Model | `llama3.2:3b` | `llama-3.3-70b-versatile` |
| Config | `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT` | `GROQ_API_KEY`, `GROQ_MODEL` |

**Why:** Ollama requires a running local server, which isn't possible on Railway. Groq provides free API access to Llama 3.3 70B — significantly more capable than the local 3B model, with faster inference (hardware-optimized).

**Key implementation changes in `llm.py`:**
- `OllamaService` → `GroqService` (internal rename; factory function `get_ollama_service()` preserved for backward compatibility)
- Streaming uses Groq's async streaming: `await client.chat.completions.create(stream=True)` + `async for chunk in stream`
- Prompt templates and system prompts preserved exactly
- All function signatures preserved: `generate()`, `generate_streaming()`, `generate_with_context()`, `generate_with_context_streaming()`, `check_health()`

---

### Local Redis → Upstash Redis

| | Before | After |
|---|---|---|
| Package | `redis==5.0.1` | `upstash-redis>=1.0.0` |
| Protocol | TCP socket | HTTPS REST |
| Hosting | Local Docker | Upstash serverless |
| Config | `REDIS_URL` | `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` |

**Why:** TCP Redis requires a persistent connection and a running server process. Upstash Redis uses HTTP REST, making it compatible with serverless and ephemeral environments. No connection management needed.

**Key implementation changes in `cache.py`:**
- `Redis.from_url()` async client → `upstash_redis.Redis(url=..., token=...)` sync HTTP client
- All async methods preserved by wrapping sync Upstash calls with `asyncio.to_thread()`
- `close()` method is now a no-op (HTTP clients have no persistent connection)
- All cache key formats, TTL values, and invalidation logic unchanged

---

## New Feature: GitHub URL Ingestion

**File:** `backend/app/services/github_ingestion.py`

### How It Works

1. User pastes a GitHub URL in the new "GitHub Repo" tab in UploadPanel
2. Frontend calls `POST /api/v1/ingest/github`
3. Backend validates the URL against `https://github.com/owner/repo` pattern
4. GitHub REST API is queried to get repo size (warns >200MB, rejects >500MB)
5. `gitpython` clones the repo with `depth=1` (latest commit only, fast)
6. The clone directory is passed to the **existing** `IngestionService.ingest_directory()`
   — no duplication of chunking/embedding/storage logic
7. Temp directory is cleaned up after ingestion
8. Response includes repo name, file counts, chunk counts, collection name, time taken
9. Frontend auto-activates the new collection so the user can chat immediately

### Collection Naming

GitHub repos are stored in their own Qdrant collection: `owner-repo` (slashes and dots replaced with hyphens, lowercased). E.g., `expressjs/express` → `expressjs-express`.

### Supported File Types

Same as file upload: `.py .js .ts .tsx .jsx .java .go .md .cpp .c .h .rs`

---

## Free Tier Limits

| Service | Free Tier Limit | Notes |
|---|---|---|
| Groq | 14,400 req/day, 6,000 tokens/min | More than enough for personal use |
| HuggingFace Inference API | ~30,000 chars/month on free | Embeddings are cached, so actual usage is much lower |
| Qdrant Cloud | 1GB storage, 1 cluster | ~1M 384-dim vectors |
| Upstash Redis | 10,000 req/day, 256MB | With 24h embedding cache, real usage is low |
| Railway | $5 credit/month | Roughly 500 hours of a small instance |
| Vercel | Unlimited for hobby projects | Static frontend with SPA routing |

---

## How to Roll Back to Local Stack

If you need to run locally again:

1. **Restore the original packages:**
   ```
   chromadb==0.4.18
   sentence-transformers==2.2.2
   torch==2.1.1
   redis==5.0.1
   ```

2. **Restore the git history** (each service was fully replaced, not patched):
   ```bash
   git diff HEAD~1 -- backend/app/services/retrieval.py
   git checkout <commit-before-migration> -- backend/app/services/
   ```

3. **Restore config.py** to re-add `ollama_*`, `chroma_*`, and `redis_url` settings.

4. **Start local services:**
   ```bash
   ollama serve && ollama pull llama3.2:3b
   redis-server
   # ChromaDB runs in-process, no separate service needed
   ```

5. **Use the dev Docker Compose:**
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```
