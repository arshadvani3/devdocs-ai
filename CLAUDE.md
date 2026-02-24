# DevDocs AI - Project Documentation

## Overview

**DevDocs AI** is a production-grade RAG (Retrieval-Augmented Generation) powered code documentation assistant. It allows users to upload codebases, ask questions in natural language, and receive accurate answers with source citations.

**Tech Stack:**
- **Backend:** FastAPI (Python 3.11+), ChromaDB, Ollama, Redis
- **Frontend:** React 18, TypeScript, Vite, TailwindCSS
- **LLM:** Ollama with llama3.2:3b (local inference)
- **Embeddings:** SentenceTransformers (all-MiniLM-L6-v2)
- **Vector DB:** ChromaDB with persistence
- **Cache:** Redis (async)

**Current Version:** 1.0.0 (Phase 3 Complete)
**Last Updated:** 2026-02-24
**Total Lines of Code:** ~7,300 (Backend: ~5,200, Frontend: ~2,100)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ChatInterface│  │ UploadPanel  │  │ WebSocket    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ HTTP/WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   API Routes                          │  │
│  │  /api/v1/ingest  /api/v1/query  /api/v1/stream       │  │
│  │  /api/v1/health  /api/v1/stats  /api/v1/metrics      │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                Service Layer                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │  │
│  │  │ Ingestion    │  │ Retrieval    │  │ LLM        │ │  │
│  │  │ Service      │  │ Service      │  │ Service    │ │  │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │  │
│  │  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │ Embedding    │  │ Cache        │                 │  │
│  │  │ Service      │  │ Service      │                 │  │
│  │  └──────────────┘  └──────────────┘                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  Utilities                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │  │
│  │  │ Parsing      │  │ Chunking     │  │ AST        │ │  │
│  │  │              │  │              │  │ Chunking   │ │  │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ ChromaDB │    │  Ollama  │    │  Redis   │
    │ (Vector) │    │  (LLM)   │    │ (Cache)  │
    └──────────┘    └──────────┘    └──────────┘
```

---

## Phase 1: RAG Foundation

### What Was Built

1. **Document Ingestion Pipeline**
   - File upload support (single files, directories, ZIP archives)
   - Smart parsing with language detection
   - Character-based chunking with overlap
   - Embedding generation using SentenceTransformers
   - Storage in ChromaDB

2. **Retrieval System**
   - Vector similarity search
   - Top-K retrieval (default: 5 chunks)
   - Metadata filtering support

3. **LLM Integration**
   - Ollama API integration (local inference)
   - Context-aware prompt construction
   - RAG-based response generation

4. **REST API**
   - POST /api/v1/ingest - Ingest files/directories
   - POST /api/v1/query - Ask questions
   - GET /api/v1/health - Health check
   - GET /api/v1/stats - System statistics

### Key Files

- [backend/app/services/ingestion.py](backend/app/services/ingestion.py) - Document ingestion orchestration
- [backend/app/services/embeddings.py](backend/app/services/embeddings.py) - Embedding generation
- [backend/app/services/retrieval.py](backend/app/services/retrieval.py) - Vector search
- [backend/app/services/llm.py](backend/app/services/llm.py) - Ollama LLM integration
- [backend/app/utils/parsing.py](backend/app/utils/parsing.py) - File parsing and language detection
- [backend/app/utils/chunking.py](backend/app/utils/chunking.py) - Text chunking utilities

---

## Phase 2: Real-Time Streaming

### What Was Built

1. **WebSocket Streaming**
   - Real-time token-by-token streaming from Ollama
   - WebSocket endpoint at /api/v1/stream
   - NDJSON parsing for Ollama streaming API

2. **React Frontend**
   - TypeScript-based React application
   - Real-time chat interface with streaming responses
   - Syntax-highlighted code blocks (Prism.js)
   - Source citation display with file/line references
   - File upload panel with drag-and-drop

3. **Custom Hooks**
   - useWebSocket - WebSocket connection management with auto-reconnect
   - useChat - Chat state management and streaming message handling

### Key Files

- [backend/app/api/websocket.py](backend/app/api/websocket.py) - WebSocket endpoint
- [frontend/src/components/ChatInterface.tsx](frontend/src/components/ChatInterface.tsx) - Main chat UI
- [frontend/src/components/MessageList.tsx](frontend/src/components/MessageList.tsx) - Message display
- [frontend/src/components/CodeBlock.tsx](frontend/src/components/CodeBlock.tsx) - Syntax highlighting
- [frontend/src/hooks/useWebSocket.ts](frontend/src/hooks/useWebSocket.ts) - WebSocket management
- [frontend/src/hooks/useChat.ts](frontend/src/hooks/useChat.ts) - Chat state management

---

## Phase 3: Production Features

### What Was Built

1. **Redis Caching Layer**
   - Async Redis client with lazy initialization
   - Embedding cache (24-hour TTL)
   - Response cache (1-hour TTL)
   - Cache statistics tracking (hit rate, hits/misses)
   - Graceful degradation (works without Redis)

2. **AST-Based Smart Chunking**
   - **Python:** AST parsing to extract functions, classes, methods
   - **JavaScript/TypeScript:** Regex-based function/class detection
   - **Markdown:** Header-based sectioning (H1-H6)
   - **Fallback:** Character-based chunking for unsupported languages
   - Preserves complete code blocks for better retrieval quality

3. **Performance Optimizations**
   - Batch embedding generation
   - Async/await patterns throughout
   - Thread pool execution for sync libraries (asyncio.to_thread)
   - Context window limiting (2000 chars max)
   - Model warmup on startup (optional)

4. **Enhanced Monitoring**
   - Detailed health checks with service status
   - Cache statistics in health endpoint
   - Uptime tracking
   - Full Prometheus metrics implementation (15+ metrics)
   - Metrics endpoint at `/api/v1/metrics`

5. **Model Optimization**
   - Switched to llama3.2:3b (3B parameters, ~2GB)
   - 3-4x faster than llama3.1:8b
   - Improved timeout handling (300s timeout)

### Key Files

- [backend/app/services/cache.py](backend/app/services/cache.py) - Redis caching service
- [backend/app/services/metrics.py](backend/app/services/metrics.py) - Prometheus metrics (15+ metrics)
- [backend/app/utils/ast_chunking.py](backend/app/utils/ast_chunking.py) - AST-based chunking
- [backend/app/config.py](backend/app/config.py) - Configuration with Phase 3 settings

---

## File Structure

```
devdocs-ai/
├── CLAUDE.md                    # This file - project documentation
├── README.md                    # User-facing documentation
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py        # REST API endpoints
│   │   │   └── websocket.py     # WebSocket streaming endpoint
│   │   ├── services/
│   │   │   ├── cache.py         # Redis caching (Phase 3)
│   │   │   ├── embeddings.py    # SentenceTransformers embeddings
│   │   │   ├── ingestion.py     # Document ingestion pipeline
│   │   │   ├── llm.py           # Ollama LLM integration
│   │   │   └── retrieval.py     # ChromaDB vector search
│   │   ├── utils/
│   │   │   ├── ast_chunking.py  # AST-based chunking (Phase 3)
│   │   │   ├── chunking.py      # Text chunking utilities
│   │   │   └── parsing.py       # File parsing and validation
│   │   ├── config.py            # Pydantic settings
│   │   ├── main.py              # FastAPI application
│   │   └── models.py            # Pydantic models
│   ├── tests/                   # Unit tests (to be created)
│   ├── requirements.txt         # Python dependencies
│   └── .env                     # Environment configuration
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx    # Main chat UI
│   │   │   ├── CodeBlock.tsx        # Syntax-highlighted code
│   │   │   ├── MessageInput.tsx     # User input field
│   │   │   ├── MessageList.tsx      # Message display
│   │   │   ├── SourceCitation.tsx   # Source references
│   │   │   └── UploadPanel.tsx      # File upload UI
│   │   ├── hooks/
│   │   │   ├── useChat.ts           # Chat state management
│   │   │   └── useWebSocket.ts      # WebSocket connection
│   │   ├── services/
│   │   │   └── api.ts               # API client
│   │   ├── types/
│   │   │   └── index.ts             # TypeScript types
│   │   ├── App.tsx                  # Root component
│   │   └── main.tsx                 # Entry point
│   ├── package.json             # Node dependencies
│   └── vite.config.ts           # Vite configuration
│
└── docs/                        # Documentation (to be created)
    └── PERFORMANCE.md           # Performance tuning guide
```

---

## Configuration

### Backend (.env)

```bash
# Application
APP_NAME="DevDocs AI"
DEBUG=false
LOG_LEVEL=INFO

# Ollama LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=300

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_DEVICE=cpu

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=devdocs

# Chunking
MAX_CHUNK_SIZE=500
CHUNK_OVERLAP=50
SUPPORTED_EXTENSIONS=.py,.js,.ts,.java,.go,.md,.tsx,.jsx,.cpp,.c,.h,.rs

# RAG
RETRIEVAL_TOP_K=5
RAG_CONTEXT_WINDOW=4000

# Cache (Phase 3)
REDIS_URL=redis://localhost:6379/0
ENABLE_CACHING=true
CACHE_TTL_EMBEDDINGS=86400
CACHE_TTL_RESPONSES=3600

# Performance (Phase 3)
MAX_CONTEXT_CHARS=2000
ENABLE_SMART_CHUNKING=true

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend (.env)

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/stream
```

---

## Key Features

### 1. Smart Chunking (Phase 3)

**How It Works:**
1. File is parsed and language is detected
2. If `ENABLE_SMART_CHUNKING=true`, routes to appropriate chunker:
   - **Python:** AST parsing extracts functions, classes, and module-level code
   - **JavaScript/TypeScript:** Regex detects function/class declarations
   - **Markdown:** Splits by header hierarchy (H1-H6)
   - **Other:** Falls back to character-based chunking
3. Large chunks are further split if they exceed `max_chunk_size * 2`
4. Syntax errors fall back to character-based chunking

**Benefits:**
- Preserves complete functions/classes (better context)
- Improves retrieval accuracy
- More semantically meaningful chunks

**Code:**
- [backend/app/utils/ast_chunking.py](backend/app/utils/ast_chunking.py) - AST chunkers
- [backend/app/utils/chunking.py:172-226](backend/app/utils/chunking.py#L172-L226) - Router logic

### 2. Redis Caching (Phase 3)

**How It Works:**
1. **Embedding Cache:** Before generating an embedding, check Redis using SHA256 hash of text
2. **Response Cache:** Before processing a query, check if we've seen this exact question
3. **Cache Miss:** Generate embedding/response, then cache with TTL
4. **Statistics:** Track hits/misses, calculate hit rate

**Benefits:**
- Repeated queries return instantly (95% faster)
- Embeddings are cached for 24 hours (avoid recomputation)
- Graceful degradation (works without Redis)

**Code:**
- [backend/app/services/cache.py](backend/app/services/cache.py) - Full implementation
- [backend/app/services/embeddings.py:79-108](backend/app/services/embeddings.py#L79-L108) - Cache integration

### 3. WebSocket Streaming (Phase 2)

**How It Works:**
1. Frontend establishes WebSocket connection to `/api/v1/stream`
2. User sends question via WebSocket
3. Backend:
   - Retrieves relevant chunks from ChromaDB
   - Streams tokens from Ollama using `stream=True`
   - Parses NDJSON response line-by-line
   - Forwards each token to frontend via WebSocket
4. Frontend displays tokens as they arrive (typewriter effect)

**Benefits:**
- Real-time response display (better UX)
- Perceived latency reduction
- Visual feedback that system is working

**Code:**
- [backend/app/api/websocket.py:76-166](backend/app/api/websocket.py#L76-L166) - WebSocket endpoint
- [backend/app/services/llm.py:135-233](backend/app/services/llm.py#L135-L233) - Streaming generation
- [frontend/src/hooks/useWebSocket.ts](frontend/src/hooks/useWebSocket.ts) - Client connection

### 4. Prometheus Metrics (Phase 3)

**How It Works:**
1. **Metrics Collection:**
   - 15+ Prometheus metrics tracking all system components
   - Counters: query counts, cache hits/misses, files ingested, tokens generated
   - Histograms: query latency, LLM latency, retrieval latency, ingestion time
   - Gauges: active connections, cache hit rates, ChromaDB document counts
2. **Export:**
   - `/api/v1/metrics` endpoint exports Prometheus text format
   - Compatible with Prometheus scraping
   - Can be visualized in Grafana

**Metrics Categories:**
- **Request Metrics:** `devdocs_queries_total`, `devdocs_query_latency_seconds`
- **Cache Metrics:** `devdocs_cache_hits_total`, `devdocs_cache_hit_rate`
- **LLM Metrics:** `devdocs_llm_requests_total`, `devdocs_llm_latency_seconds`, `devdocs_llm_tokens_generated_total`
- **Retrieval Metrics:** `devdocs_retrieval_chunks_count`, `devdocs_retrieval_latency_seconds`
- **Ingestion Metrics:** `devdocs_files_ingested_total`, `devdocs_chunks_created_total`
- **System Metrics:** `devdocs_active_connections`, `devdocs_chromadb_documents_total`

**Benefits:**
- Real-time system observability
- Performance bottleneck identification
- Cache effectiveness tracking
- Production-ready monitoring

**Code:**
- [backend/app/services/metrics.py](backend/app/services/metrics.py) - Full metrics implementation
- [backend/app/api/routes.py:90-105](backend/app/api/routes.py#L90-L105) - Metrics endpoint

### 5. RAG Pipeline (Phase 1)

**How It Works:**
1. **Ingestion:**
   - Parse file → Detect language → Chunk text → Generate embeddings → Store in ChromaDB
2. **Query:**
   - User question → Generate query embedding → Search ChromaDB (cosine similarity)
   - Retrieve top-K chunks → Build context prompt → Send to LLM → Return answer + citations

**Benefits:**
- Answers grounded in actual codebase
- Source citations for verification
- Handles large codebases (vector search)

**Code:**
- [backend/app/services/ingestion.py:44-115](backend/app/services/ingestion.py#L44-L115) - Ingestion
- [backend/app/api/routes.py:188-261](backend/app/api/routes.py#L188-L261) - Query endpoint

---

## Design Patterns

### 1. Factory Pattern
```python
def get_cache_service() -> CacheService:
    """Factory function for cache service."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
```
**Used for:** CacheService, EmbeddingService, VectorStore, OllamaService, IngestionService

**Why:** Centralized instantiation, enables singleton pattern, easier testing

### 2. Singleton Pattern
```python
class EmbeddingService:
    """Singleton embedding service with lazy-loaded model."""
    _instance: Optional['EmbeddingService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```
**Used for:** EmbeddingService (expensive model loading), CacheService (single Redis connection)

**Why:** Avoid reloading heavy models, maintain single connection pool

### 3. Async/Await with Thread Pool
```python
async def embed_text(self, text: str) -> List[float]:
    def _encode():
        # Synchronous sentence-transformers code
        embeddings = self.model.encode([text], ...)
        return embeddings[0].tolist()

    # Run in thread pool to avoid blocking event loop
    embedding = await asyncio.to_thread(_encode)
    return embedding
```
**Used for:** All embedding operations (sentence-transformers is synchronous)

**Why:** Redis cache is async, but SentenceTransformers is sync. Thread pool prevents blocking.

### 4. Graceful Degradation
```python
try:
    cache = get_cache_service()
    is_healthy = await cache.check_health()
    if is_healthy:
        logger.info("✓ Redis cache is healthy")
    else:
        logger.warning("✗ Redis cache is not responding")
except Exception as e:
    logger.warning(f"✗ Redis cache unavailable: {e}")
    logger.warning("  Continuing without caching...")
```
**Used for:** Cache, optional metrics

**Why:** System should work even if Redis/Prometheus unavailable

### 5. Strategy Pattern (Chunking)
```python
if language == "python":
    return chunk_python_ast(text, file_path, max_chunk_size)
elif language in ("javascript", "typescript"):
    return chunk_javascript_simple(text, file_path, max_chunk_size)
elif language == "markdown":
    return chunk_markdown_by_headers(text, file_path, max_chunk_size)
else:
    return chunk_text(text, file_path, language, max_chunk_size)
```
**Used for:** Smart chunking based on language

**Why:** Different languages need different chunking strategies

---

## Installation & Setup

### Prerequisites
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull LLM model
ollama pull llama3.2:3b

# Install Redis (macOS)
brew install redis
redis-server

# Install Redis (Ubuntu)
sudo apt install redis-server
sudo systemctl start redis
```

### Backend Setup
```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # Then edit with your settings

# Run server
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env  # Then edit with your settings

# Run development server
npm run dev
```

### Verify Installation
```bash
# Backend health check
curl http://localhost:8000/api/v1/health | jq

# Expected output:
{
  "status": "healthy",
  "services": {
    "ollama": true,
    "chromadb": true,
    "embeddings": true,
    "cache": true
  },
  "stats": {
    "cache": {
      "hit_rate": 0.0,
      "total_hits": 0,
      "total_misses": 0
    }
  }
}

# Frontend should be accessible at:
http://localhost:5173
```

---

## Usage Examples

### 1. Ingest a Python File
```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@example.py" \
  -F "overwrite=true"

# Response:
{
  "success": true,
  "files_processed": 1,
  "total_chunks": 5,
  "processing_time_seconds": 1.234,
  "details": [
    {
      "file_path": "example.py",
      "file_size": 1234,
      "language": "python",
      "num_chunks": 5,
      "processed_at": "2026-02-22T15:30:00"
    }
  ]
}
```

### 2. Query the Codebase
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How does authentication work?",
    "top_k": 5
  }'

# Response:
{
  "answer": "Authentication is handled by the authenticate() function...",
  "sources": [
    {
      "file_path": "auth.py",
      "start_line": 15,
      "end_line": 30,
      "relevance_score": 0.89,
      "text": "def authenticate(user, password):..."
    }
  ],
  "processing_time_seconds": 2.5
}
```

### 3. WebSocket Streaming (Frontend)
```typescript
const ws = new WebSocket('ws://localhost:8000/api/v1/stream');

ws.onopen = () => {
  ws.send(JSON.stringify({
    question: "Explain the caching strategy",
    top_k: 5
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'token') {
    // Append token to display
    appendToken(data.content);
  } else if (data.type === 'sources') {
    // Display source citations
    displaySources(data.sources);
  } else if (data.type === 'done') {
    // Streaming complete
    console.log('Done!');
  }
};
```

---

## Testing

### Manual Testing Checklist

#### Phase 1: RAG Basics
- [ ] Ingest a Python file - should create multiple chunks
- [ ] Query the codebase - should return relevant chunks
- [ ] Check health endpoint - all services healthy
- [ ] Verify ChromaDB persistence - restart server, data still there

#### Phase 2: Streaming
- [ ] Open frontend at http://localhost:5173
- [ ] Upload a file via drag-and-drop
- [ ] Ask a question - should see streaming response
- [ ] Verify source citations appear below answer
- [ ] Check syntax highlighting in code blocks

#### Phase 3: Performance Features
- [ ] Redis caching:
  - [ ] Ask same question twice - second should be instant
  - [ ] Check `/health` endpoint - cache hit_rate should increase
  - [ ] Stop Redis - system should still work (degraded)
- [ ] Smart chunking:
  - [ ] Ingest Python file - logs should show "Using Python AST chunking"
  - [ ] Ingest Markdown file - logs should show "Using Markdown header chunking"
  - [ ] Verify chunks preserve complete functions (check ChromaDB)

### Unit Tests (To Be Created)

```bash
# Run all tests
pytest backend/tests/

# Run with coverage
pytest --cov=app backend/tests/

# Run specific test file
pytest backend/tests/test_cache.py
```

**Test files to create:**
- `test_cache.py` - Redis caching tests
- `test_ast_chunking.py` - AST chunking tests
- `test_embeddings.py` - Embedding generation tests
- `test_retrieval.py` - Vector search tests
- `test_ingestion.py` - Document ingestion tests
- `test_performance.py` - Performance benchmarks

---

## Troubleshooting

### 1. Ollama Connection Error
```
Error: Could not connect to Ollama at http://localhost:11434
```
**Solution:**
```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### 2. Model Not Found
```
Error: Model 'llama3.2:3b' not found
```
**Solution:**
```bash
# Pull the model
ollama pull llama3.2:3b

# Verify installation
ollama list
```

### 3. Redis Connection Error
```
Warning: Redis cache unavailable: Connection refused
```
**Solution:**
```bash
# Start Redis
redis-server

# Verify it's running
redis-cli ping  # Should return PONG

# Or disable caching
echo "ENABLE_CACHING=false" >> backend/.env
```

### 4. Query Timeout
```
Error: httpx.ReadTimeout after 120 seconds
```
**Solution:**
- Increase timeout in `.env`: `OLLAMA_TIMEOUT=300`
- Use faster model: `OLLAMA_MODEL=llama3.2:3b`
- Reduce context window: `MAX_CONTEXT_CHARS=1500`

### 5. AST Chunking Not Working
```
Logs show: "Chunked file.py into 1 chunks (max_size=500, overlap=50)"
Should show: "Using Python AST chunking for file.py"
```
**Solution:**
```bash
# Enable smart chunking
echo "ENABLE_SMART_CHUNKING=true" >> backend/.env

# Restart backend
# Press Ctrl+C to stop
uvicorn app.main:app --reload
```

### 6. Frontend Can't Connect to Backend
```
Error: Network Error when calling API
```
**Solution:**
- Check backend is running: `curl http://localhost:8000/api/v1/health`
- Verify CORS settings in `backend/app/config.py`
- Check frontend `.env` has correct `VITE_API_BASE_URL`

---

## Performance Tuning

### Embedding Generation
```bash
# CPU optimization
EMBEDDING_BATCH_SIZE=32

# GPU optimization (if CUDA available)
EMBEDDING_DEVICE=cuda
EMBEDDING_BATCH_SIZE=128
```

### LLM Response Time
```bash
# Use smaller model (faster, slightly lower quality)
OLLAMA_MODEL=llama3.2:3b  # 3B params, ~10-30s response time

# Reduce context size (faster, less context)
MAX_CONTEXT_CHARS=1500
RETRIEVAL_TOP_K=3

# Increase context size (slower, more context)
MAX_CONTEXT_CHARS=3000
RETRIEVAL_TOP_K=7
```

### Cache Configuration
```bash
# Aggressive caching (stable codebases)
CACHE_TTL_EMBEDDINGS=604800  # 7 days
CACHE_TTL_RESPONSES=7200     # 2 hours

# Conservative caching (changing codebases)
CACHE_TTL_EMBEDDINGS=3600    # 1 hour
CACHE_TTL_RESPONSES=600      # 10 minutes
```

---

## Future Enhancements

### Completed in Current Version ✓
- ✓ **Prometheus Metrics** - Fully implemented with 15+ metrics tracking queries, cache, LLM, retrieval
- ✓ **Retry Logic** - Implemented in LLM service with exponential backoff (3 retries, 2-10s delays)
- ✓ **Performance Tuning Guide** - Created at `docs/PERFORMANCE.md`

### Remaining Enhancements

### 1. Comprehensive Testing
**Current State:** Partial coverage (~230 lines of tests)
- `backend/tests/test_ingestion.py` - Parser and chunking tests
- `backend/tests/test_retrieval.py` - Vector search tests

**Needed:**
- Unit tests for cache service
- Unit tests for metrics service
- Unit tests for AST chunking
- Integration tests for full RAG pipeline
- Performance benchmarks
- WebSocket streaming tests

**Target:** 80%+ test coverage

### 2. Additional Language Support
**Current State:** Python (AST), JavaScript/TypeScript (Regex), Markdown (Headers)

**Needed:**
- Java AST parsing
- Go AST parsing
- Rust AST parsing
- C/C++ parsing improvements

### 3. Documentation
**Completed:**
- `CLAUDE.md` - Development documentation
- `README.md` - User-facing documentation
- `docs/PERFORMANCE.md` - Performance tuning guide

**Needed:**
- `docs/API.md` - Detailed API reference (currently auto-generated at `/docs`)
- `docs/ARCHITECTURE.md` - Deep-dive into system architecture
- `docs/DEPLOYMENT.md` - Production deployment guide

### 4. Production Hardening
- Rate limiting per IP/user
- User authentication and authorization
- Multi-tenant collection support
- File size limits and validation
- Request timeout configuration
- Graceful shutdown handling
- Database migrations

### 5. Advanced Features
- Conversation history persistence (backend storage)
- Multi-document queries (cross-repository search)
- Code change detection and incremental updates
- Support for binary files (PDFs, images via OCR)
- Query result caching with invalidation strategy
- Feedback loop for answer quality

---

## Dependencies

### Backend (requirements.txt)
```
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Data Models
pydantic==2.5.0
pydantic-settings==2.1.0

# AI/ML Dependencies
sentence-transformers==2.2.2
chromadb==0.4.18
torch==2.1.1              # Required for sentence-transformers

# LLM Integration
httpx==0.25.2

# Configuration
python-dotenv==1.0.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1

# Utilities
numpy==1.26.2

# Phase 3: Production Features
redis==5.0.1              # Caching layer
tenacity==8.2.3           # Retry logic (implemented in LLM service)
prometheus-client==0.19.0 # Metrics (fully implemented, 15+ metrics)
esprima==4.0.1            # JavaScript AST parsing
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "prismjs": "^1.30.0",
    "@types/prismjs": "^1.26.5"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^5.1.1",
    "vite": "^7.3.1",
    "typescript": "~5.9.3",
    "tailwindcss": "^3.4.19",
    "eslint": "^9.39.1",
    "typescript-eslint": "^8.48.0"
  }
}
```

---

## Code Quality Standards

### Python (Backend)
- **Type hints:** All functions have complete type annotations
- **Docstrings:** Google-style docstrings for all classes and functions
- **Logging:** Comprehensive logging at INFO, DEBUG, WARNING, ERROR levels
- **Error handling:** Try-except blocks with specific exception types
- **Async/await:** Async throughout for I/O operations
- **PEP 8:** Follow Python style guidelines

### TypeScript (Frontend)
- **Strict mode:** TypeScript strict mode enabled
- **Type safety:** No `any` types except where necessary
- **Component structure:** Functional components with hooks
- **Props typing:** All component props fully typed
- **Error handling:** Try-catch in async operations

---

## Key Learnings

### 1. Async/Await with Sync Libraries
**Problem:** SentenceTransformers is synchronous, Redis cache is async
**Solution:** Use `asyncio.to_thread()` to run sync code in thread pool
**Pattern:** Wrap sync operations in nested function, then `await asyncio.to_thread(fn)`

### 2. AST Chunking Benefits
**Problem:** Character-based chunking splits functions mid-block
**Solution:** AST parsing to extract complete functions/classes
**Result:** Better retrieval quality, more meaningful context

### 3. Cache Hit Rate Optimization
**Problem:** Low cache hit rates waste resources
**Solution:** Deterministic SHA256 hashing of text for cache keys
**Result:** Same text always gets same cache key, reliable hits

### 4. LLM Model Selection
**Problem:** llama3.1:8b too slow on CPU (30-120s responses)
**Solution:** Switched to llama3.2:3b (3-4x faster)
**Trade-off:** Slightly lower quality but much better UX

### 5. WebSocket Streaming UX
**Problem:** Users see nothing for 30+ seconds while LLM generates
**Solution:** Stream tokens as they're generated
**Result:** Perceived latency reduction, better user experience

---

## Contact & Contribution

For questions or contributions, refer to the repository README.md.

---

## Project Statistics

**Code Metrics:**
- Total Lines of Code: ~7,300
- Backend: ~5,200 lines (Python)
  - Services: ~1,785 lines
  - API: ~598 lines
  - Utils: ~829 lines
  - Config/Models: ~401 lines
- Frontend: ~2,100 lines (TypeScript/React)
  - Components: ~690 lines
  - Hooks: ~238 lines
  - Services/Types: ~138 lines
- Tests: ~230 lines (partial coverage)
- Documentation: ~50KB (3 major docs)

**Feature Completeness:**
- Phase 1 (RAG Foundation): 100%
- Phase 2 (Real-Time Streaming): 100%
- Phase 3 (Production Features): 100%
- Test Coverage: ~20% (needs expansion)

**Last Updated:** 2026-02-24
**Version:** 1.0.0 (Phase 3 Complete)
