"""
Pydantic models for API requests, responses, and internal data structures.

These models provide type safety, validation, and automatic documentation
for the DevDocs AI API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


# ============================================================================
# Document Processing Models
# ============================================================================

class DocumentChunk(BaseModel):
    """
    Represents a chunk of code/documentation with metadata.

    This is the core data structure stored in the vector database.
    Each chunk contains the actual text content plus metadata for
    traceability and citation.
    """
    id: str = Field(..., description="Unique identifier for the chunk")
    text: str = Field(..., description="The actual text content of the chunk")
    file_path: str = Field(..., description="Original file path")
    start_line: int = Field(..., ge=1, description="Starting line number in original file")
    end_line: int = Field(..., ge=1, description="Ending line number in original file")
    language: str = Field(..., description="Programming language or file type")
    chunk_index: int = Field(..., ge=0, description="Index of this chunk within the file")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding (384-dim for MiniLM)")

    @validator("end_line")
    def validate_line_numbers(cls, v, values):
        """Ensure end_line >= start_line."""
        if "start_line" in values and v < values["start_line"]:
            raise ValueError("end_line must be >= start_line")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "file_123_chunk_0",
                "text": "def hello_world():\n    print('Hello, World!')",
                "file_path": "src/main.py",
                "start_line": 1,
                "end_line": 2,
                "language": "python",
                "chunk_index": 0
            }
        }


class FileMetadata(BaseModel):
    """Metadata about an uploaded file."""
    file_path: str
    file_size: int  # bytes
    language: str
    num_chunks: int
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# API Request Models
# ============================================================================

class IngestRequest(BaseModel):
    """
    Request model for document ingestion.

    Note: The actual file upload is handled via FastAPI's UploadFile,
    but this model can hold additional metadata.
    """
    collection_name: Optional[str] = Field(
        None,
        description="Custom collection name (defaults to configured collection)"
    )
    overwrite: bool = Field(
        False,
        description="Whether to overwrite existing documents with same file_path"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "collection_name": "my_project",
                "overwrite": False
            }
        }


class QueryRequest(BaseModel):
    """Request model for querying the knowledge base."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The question to ask about the codebase"
    )
    collection_name: Optional[str] = Field(
        None,
        description="Collection to query (defaults to configured collection)"
    )
    top_k: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Number of relevant chunks to retrieve (defaults to configured top_k)"
    )
    include_sources: bool = Field(
        True,
        description="Whether to include source citations in response"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question": "How does the authentication system work?",
                "top_k": 5,
                "include_sources": True
            }
        }


# ============================================================================
# API Response Models
# ============================================================================

class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    success: bool
    message: str
    files_processed: int
    total_chunks: int
    collection_name: str
    processing_time_seconds: float
    file_metadata: List[FileMetadata] = []

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully processed 3 files",
                "files_processed": 3,
                "total_chunks": 45,
                "collection_name": "code_docs",
                "processing_time_seconds": 2.34,
                "file_metadata": []
            }
        }


class SourceCitation(BaseModel):
    """Citation for a source document used in the answer."""
    file_path: str
    start_line: int
    end_line: int
    text_snippet: str = Field(..., description="Snippet of the relevant text")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "src/auth.py",
                "start_line": 15,
                "end_line": 25,
                "text_snippet": "def authenticate_user(username, password)...",
                "relevance_score": 0.87
            }
        }


class QueryResponse(BaseModel):
    """Response model for queries."""
    success: bool
    question: str
    answer: str
    sources: List[SourceCitation] = []
    processing_time_seconds: float
    model_used: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "question": "How does authentication work?",
                "answer": "The authentication system uses JWT tokens...",
                "sources": [],
                "processing_time_seconds": 1.23,
                "model_used": "llama3.1:8b"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, bool] = Field(
        default_factory=dict,
        description="Status of dependent services (ollama, chromadb, embeddings, cache)"
    )
    version: str = "1.0.0"
    stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional statistics (cache hit rates, document counts, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T12:00:00",
                "services": {
                    "ollama": True,
                    "chromadb": True,
                    "embeddings": True,
                    "cache": True
                },
                "version": "1.0.0",
                "stats": {
                    "cache": {
                        "hit_rate": 0.75,
                        "total_hits": 150,
                        "total_misses": 50
                    }
                }
            }
        }


# ============================================================================
# GitHub Ingestion Models
# ============================================================================

class GitHubIngestRequest(BaseModel):
    """Request model for GitHub repository ingestion."""
    repo_url: str = Field(
        ...,
        description="Public GitHub repository URL (e.g. https://github.com/expressjs/express)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/expressjs/express"
            }
        }


class GitHubIngestResponse(BaseModel):
    """Response model for GitHub repository ingestion."""
    success: bool
    repo_url: str
    repo_name: str
    total_files: int
    processed_files: int
    total_chunks: int
    collection_name: str
    time_taken_seconds: float

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "repo_url": "https://github.com/expressjs/express",
                "repo_name": "expressjs/express",
                "total_files": 45,
                "processed_files": 20,
                "total_chunks": 284,
                "collection_name": "expressjs-express",
                "time_taken_seconds": 12.3
            }
        }


# ============================================================================
# Error Response Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "File processing failed",
                "detail": "Unsupported file extension: .exe",
                "timestamp": "2024-01-15T12:00:00"
            }
        }
