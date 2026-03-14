"""
Application configuration management using Pydantic settings.

This module handles all environment variables and configuration settings
for the DevDocs AI application (cloud-hosted stack).
"""

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        app_name: Application name for logging and identification
        debug: Enable debug mode (verbose logging, auto-reload)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

        # Groq LLM Settings
        groq_api_key: Groq API key
        groq_model: LLM model name on Groq

        # Embedding Settings
        hf_api_key: HuggingFace Inference API key
        embedding_model: HuggingFace model name (used in HF API URL)

        # Qdrant Settings
        qdrant_url: Qdrant Cloud cluster URL
        qdrant_api_key: Qdrant Cloud API key
        qdrant_collection_name: Default collection name

        # Document Processing Settings
        max_chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks in characters
        supported_extensions: Comma-separated list of supported file extensions

        # RAG Settings
        retrieval_top_k: Number of documents to retrieve for RAG
        rag_context_window: Maximum context window for LLM

        # Cache Settings
        upstash_redis_rest_url: Upstash Redis REST endpoint URL
        upstash_redis_rest_token: Upstash Redis REST auth token
        enable_caching: Enable/disable caching layer
        cache_ttl_embeddings: TTL for cached embeddings (seconds)
        cache_ttl_responses: TTL for cached query responses (seconds)

        # Performance Settings
        max_context_chars: Max chars of context sent to LLM
        enable_smart_chunking: Use AST-based chunking for supported languages

        # API Settings
        api_host: API server host
        api_port: API server port
        cors_origins: Comma-separated list of allowed CORS origins
    """

    # Application Settings
    app_name: str = "DevDocs AI"
    debug: bool = False
    log_level: str = "INFO"

    # Groq LLM Settings
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Embedding Settings (HuggingFace Inference API)
    hf_api_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 5  # HF free tier safe batch size

    # Qdrant Cloud Settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "devdocs"

    # Document Processing Settings
    max_chunk_size: int = 500
    chunk_overlap: int = 50
    supported_extensions: str = ".py,.js,.ts,.java,.go,.md,.tsx,.jsx,.cpp,.c,.h,.rs"

    # RAG Settings
    retrieval_top_k: int = 5
    rag_context_window: int = 4000  # Characters, not tokens

    # Upstash Redis Settings
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    enable_caching: bool = True
    cache_ttl_embeddings: int = 86400   # 24 hours
    cache_ttl_responses: int = 3600     # 1 hour

    # Performance Settings
    max_context_chars: int = 2000  # Limit context to prevent overwhelming LLM

    # Chunking Settings
    enable_smart_chunking: bool = True  # Use AST-based chunking for supported languages

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = (
        "http://localhost:3000,"
        "http://localhost:5173,"
        "https://devdocs-ai.vercel.app"
    )

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
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)


# Initialize logging on module import
setup_logging()
