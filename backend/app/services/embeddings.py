"""
Embedding generation service using sentence-transformers.

This module handles loading the embedding model and generating
vector embeddings for text chunks.
"""

import logging
import asyncio
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using sentence-transformers.

    This class implements a singleton pattern to avoid loading the model
    multiple times. The model is loaded lazily on first use.

    Attributes:
        model: The loaded SentenceTransformer model
        model_name: Name of the model being used
        embedding_dim: Dimensionality of the embeddings
    """

    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the embedding service (lazy loading)."""
        self.model_name = settings.embedding_model
        self.device = settings.embedding_device
        self.batch_size = settings.embedding_batch_size

    def _load_model(self) -> None:
        """
        Load the sentence-transformer model.

        This is called lazily on first use to avoid loading the model
        during application startup if it's not needed.
        """
        if self._model is not None:
            return

        try:
            logger.info(
                f"Loading embedding model: {self.model_name} on device: {self.device}"
            )
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            logger.info(
                f"Successfully loaded {self.model_name}. "
                f"Embedding dimension: {self.embedding_dim}"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Could not load embedding model: {e}") from e

    @property
    def model(self) -> SentenceTransformer:
        """Get the model, loading it if necessary."""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Get the dimensionality of the embeddings."""
        # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        return self.model.get_sentence_embedding_dimension()

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text with caching.

        Args:
            text: Text to embed

        Returns:
            Embedding as list of floats

        Example:
            >>> service = EmbeddingService()
            >>> embedding = await service.embed_text("def hello(): pass")
            >>> len(embedding)
            384
        """
        # Try cache first
        if settings.enable_caching:
            from app.services.cache import get_cache_service
            cache = get_cache_service()
            cached_embedding = await cache.get_embedding(text)
            if cached_embedding is not None:
                logger.debug("Cache hit for embedding")
                return cached_embedding

        try:
            # Run synchronous embedding generation in thread pool
            def _encode():
                embeddings = self.model.encode(
                    [text],
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    batch_size=1,
                )
                return embeddings[0].tolist()

            embedding = await asyncio.to_thread(_encode)

            # Cache the result
            if settings.enable_caching:
                from app.services.cache import get_cache_service
                cache = get_cache_service()
                await cache.set_embedding(text, embedding)

            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding for text: {e}")
            raise

    async def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently with caching.

        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress bar

        Returns:
            List of embeddings (each embedding is a list of floats)

        Example:
            >>> service = EmbeddingService()
            >>> texts = ["def foo(): pass", "def bar(): pass"]
            >>> embeddings = await service.embed_batch(texts)
            >>> len(embeddings)
            2
        """
        if not texts:
            return []

        # Check cache for each text
        results: List[Optional[List[float]]] = []
        to_embed: List[str] = []
        to_embed_indices: List[int] = []

        if settings.enable_caching:
            from app.services.cache import get_cache_service
            cache = get_cache_service()

            for idx, text in enumerate(texts):
                cached = await cache.get_embedding(text)
                if cached:
                    results.append(cached)
                else:
                    results.append(None)  # Placeholder
                    to_embed.append(text)
                    to_embed_indices.append(idx)
        else:
            to_embed = texts
            to_embed_indices = list(range(len(texts)))
            results = [None] * len(texts)

        # Generate embeddings for uncached texts
        if to_embed:
            logger.info(f"Generating {len(to_embed)} embeddings (batch_size={self.batch_size})")

            try:
                # Run synchronous embedding generation in thread pool
                def _encode():
                    return self.model.encode(
                        to_embed,
                        convert_to_numpy=True,
                        show_progress_bar=show_progress,
                        batch_size=self.batch_size,
                    ).tolist()

                embeddings_list = await asyncio.to_thread(_encode)

                # Cache and store results
                if settings.enable_caching:
                    from app.services.cache import get_cache_service
                    cache = get_cache_service()

                    for text, embedding, original_idx in zip(to_embed, embeddings_list, to_embed_indices):
                        await cache.set_embedding(text, embedding)
                        results[original_idx] = embedding
                else:
                    results = embeddings_list

                logger.info(
                    f"Successfully generated {len(embeddings_list)} embeddings "
                    f"(dim: {len(embeddings_list[0])})"
                )

            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                raise

        return results  # type: ignore

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query.

        For some models, queries may need different processing than documents.
        For all-MiniLM-L6-v2, we use the same encoding.

        Args:
            query: Query text to embed

        Returns:
            Embedding as list of floats
        """
        return await self.embed_text(query)

    async def check_health(self) -> bool:
        """
        Check if the embedding service is working.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Try to generate a simple embedding
            test_embedding = await self.embed_text("test")
            return len(test_embedding) == self.embedding_dim
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False


# Global instance for easy access
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get the global embedding service instance.

    This function implements the singleton pattern, ensuring only
    one instance of the embedding service (and thus the model) exists.

    Returns:
        The global EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
