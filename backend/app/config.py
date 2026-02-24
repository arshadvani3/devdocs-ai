"""
Application configuration management using Pydantic settings.

This module handles all environment variables and configuration settings
for the DevDocs AI application.
"""

import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        app_name: Application name for logging and identification
        debug: Enable debug mode (verbose logging, auto-reload)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

        # Ollama LLM Settings
        ollama_base_url: Base URL for Ollama API
        ollama_model: LLM model name (e.g., llama3.1:8b)
        ollama_timeout: Request timeout in seconds

        # Embedding Settings
        embedding_model: sentence-transformers model name
        embedding_batch_size: Batch size for embedding generation
        embedding_device: Device for embeddings (cpu, cuda, mps)

        # ChromaDB Settings
        chroma_persist_directory: Directory to persist ChromaDB data
        chroma_collection_name: Default collection name

        # Document Processing Settings
        max_chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks in characters
        supported_extensions: Comma-separated list of supported file extensions

        # RAG Settings
        retrieval_top_k: Number of documents to retrieve for RAG
        rag_context_window: Maximum context window for LLM

        # API Settings
        api_host: API server host
        api_port: API server port
        cors_origins: Comma-separated list of allowed CORS origins
    """

    # Application Settings
    app_name: str = "DevDocs AI"
    debug: bool = False
    log_level: str = "INFO"

    # Ollama LLM Settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout: int = 300  # 5 minutes for complex queries (increased from 120s)

    # Embedding Settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_device: str = "cpu"  # cpu, cuda, or mps (for Apple Silicon)

    # ChromaDB Settings
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "code_docs"

    # Document Processing Settings
    max_chunk_size: int = 500
    chunk_overlap: int = 50
    supported_extensions: str = ".py,.js,.ts,.java,.go,.md,.tsx,.jsx,.cpp,.c,.h,.rs"

    # RAG Settings
    retrieval_top_k: int = 5
    rag_context_window: int = 4000  # Characters, not tokens

    # Cache Settings (Phase 3)
    redis_url: str = "redis://localhost:6379/0"
    enable_caching: bool = True
    cache_ttl_embeddings: int = 86400  # 24 hours
    cache_ttl_responses: int = 3600    # 1 hour

    # Performance Settings (Phase 3)
    max_context_chars: int = 2000  # Limit context to prevent overwhelming LLM

    # Chunking Settings (Phase 3)
    enable_smart_chunking: bool = True  # Use AST-based chunking for supported languages

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def supported_extensions_list(self) -> list[str]:
        """Convert comma-separated extensions to list."""
        return [ext.strip() for ext in self.supported_extensions.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        """Convert comma-separated CORS origins to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_chroma_path(self) -> Path:
        """Get ChromaDB persist directory as Path object."""
        path = Path(self.chroma_persist_directory)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global settings instance
settings = Settings()


def setup_logging() -> None:
    """
    Configure application logging based on settings.

    Sets up logging format, level, and handlers for the application.
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
        ]
    )

    # Set specific loggers to WARNING to reduce noise
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# Initialize logging on module import
setup_logging()
