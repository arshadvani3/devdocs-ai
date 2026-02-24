# DevDocs AI - Backend

Production-grade RAG-powered code documentation assistant backend built with FastAPI.

## Overview

The backend provides a REST API for:
- **Document Ingestion**: Upload and process code files into a vector database
- **Semantic Search**: Find relevant code snippets using embeddings
- **AI-Powered Q&A**: Ask questions and get answers with source citations

## Architecture

```
User Upload → Parser → Chunker → Embeddings → ChromaDB
                                                    ↓
User Query → Embedding → Similarity Search → Context → LLM → Answer
```

### Components

1. **Ingestion Pipeline** ([services/ingestion.py](app/services/ingestion.py))
   - Parses code files (Python, JavaScript, TypeScript, Java, Go, etc.)
   - Chunks code intelligently with overlap
   - Generates embeddings using sentence-transformers
   - Stores in ChromaDB vector database

2. **Retrieval System** ([services/retrieval.py](app/services/retrieval.py))
   - Vector similarity search using ChromaDB
   - Returns top-k most relevant code chunks
   - Includes metadata (file path, line numbers)

3. **LLM Integration** ([services/llm.py](app/services/llm.py))
   - Connects to Ollama API for local LLM inference
   - Implements RAG (Retrieval-Augmented Generation)
   - Formats prompts with retrieved context

4. **API Endpoints** ([api/routes.py](app/api/routes.py))
   - `POST /api/v1/ingest` - Upload files or ZIP archives
   - `POST /api/v1/query` - Ask questions
   - `GET /api/v1/health` - Health check
   - `GET /api/v1/stats` - Collection statistics

## Prerequisites

1. **Python 3.11+**
   ```bash
   python --version
   ```

2. **Ollama** (for local LLM)
   ```bash
   # Install Ollama from https://ollama.ai
   ollama serve

   # Pull Llama 3.1 8B model
   ollama pull llama3.1:8b
   ```

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: First run will download the embedding model (~80MB) and may take a minute.

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` if needed. Default values work for local development.

### 4. Start the Server

```bash
# Development mode (auto-reload)
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Server will start at http://localhost:8000

## API Usage

### 1. Upload Documents

Upload a single Python file:

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "file=@sample_code.py"
```

Upload a ZIP archive:

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "file=@my_project.zip"
```

Response:
```json
{
  "success": true,
  "message": "Successfully processed 3 files",
  "files_processed": 3,
  "total_chunks": 45,
  "collection_name": "code_docs",
  "processing_time_seconds": 2.34
}
```

### 2. Query the Knowledge Base

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How does the authentication system work?",
    "top_k": 5,
    "include_sources": true
  }'
```

Response:
```json
{
  "success": true,
  "question": "How does the authentication system work?",
  "answer": "The authentication system uses JWT tokens...",
  "sources": [
    {
      "file_path": "src/auth.py",
      "start_line": 15,
      "end_line": 25,
      "text_snippet": "def authenticate_user(username, password)...",
      "relevance_score": 0.87
    }
  ],
  "processing_time_seconds": 1.23,
  "model_used": "llama3.1:8b"
}
```

### 3. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### 4. Collection Stats

```bash
curl http://localhost:8000/api/v1/stats
```

## Testing

Run all tests:

```bash
pytest tests/ -v
```

Run specific test file:

```bash
pytest tests/test_ingestion.py -v
pytest tests/test_retrieval.py -v
```

Run with coverage:

```bash
pytest tests/ --cov=app --cov-report=html
```

## Configuration

Key environment variables (see [.env.example](.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.1:8b` | LLM model to use |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_db` | ChromaDB storage path |
| `MAX_CHUNK_SIZE` | `500` | Max characters per chunk |
| `RETRIEVAL_TOP_K` | `5` | Number of results to retrieve |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── services/
│   │   ├── ingestion.py     # Document processing
│   │   ├── embeddings.py    # Embedding generation
│   │   ├── retrieval.py     # Vector search
│   │   └── llm.py           # Ollama integration
│   └── utils/
│       ├── chunking.py      # Text chunking
│       └── parsing.py       # File parsing
├── tests/
│   ├── test_ingestion.py
│   └── test_retrieval.py
├── requirements.txt
└── README.md
```

## Troubleshooting

### Ollama Connection Error

**Error**: `Could not connect to Ollama`

**Solution**:
```bash
# Start Ollama server
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Model Not Found

**Error**: `Model 'llama3.1:8b' not found`

**Solution**:
```bash
ollama pull llama3.1:8b
```

### Embedding Model Download Issues

**Error**: `Failed to load embedding model`

**Solution**: The model will auto-download on first use. Ensure internet connection and wait for download (~80MB).

### ChromaDB Permission Error

**Error**: `Permission denied: ./chroma_db`

**Solution**:
```bash
mkdir chroma_db
chmod 755 chroma_db
```

## Performance Notes

- **First Request**: May take 10-15 seconds (model loading)
- **Subsequent Requests**: 1-3 seconds average
- **Embedding Generation**: ~100 chunks/second
- **LLM Inference**: 2-5 seconds (depends on context size)

## Development

### Adding New File Types

Edit [utils/parsing.py](app/utils/parsing.py):

```python
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".rs": "rust",  # Add new extension
    # ...
}
```

Update `SUPPORTED_EXTENSIONS` in `.env`.

### Changing Chunk Strategy

See [utils/chunking.py](app/utils/chunking.py) - implements character-based chunking with overlap. Future versions will support AST-based chunking.

### Using Different LLM Models

```bash
# Pull a different model
ollama pull codellama:13b

# Update .env
OLLAMA_MODEL=codellama:13b
```

## Next Steps (Phase 2+)

- [ ] WebSocket streaming for real-time responses
- [ ] React frontend with TypeScript
- [ ] Redis caching layer
- [ ] AST-based code chunking
- [ ] Multi-language support improvements
- [ ] Docker containerization
- [ ] Kubernetes deployment

## License

MIT

## Author

Built as a resume project to demonstrate AI/ML engineering and cloud infrastructure skills.
