"""
Embedding generation service using HuggingFace Inference API.

This module handles generating vector embeddings for text chunks
via the HuggingFace hosted inference API, replacing the local
SentenceTransformers model to avoid Railway size limits.
"""

import logging
import asyncio
from typing import List, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 produces 384-dimensional embeddings
HF_API_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
)
_BATCH_SIZE = 5          # max texts per HF API request
_BATCH_DELAY = 0.5       # seconds between parallel groups to avoid rate limits
_MAX_RETRIES = 5
_CONCURRENT_BATCHES = 3  # how many batches fire simultaneously
_RETRY_DELAYS = [1, 2, 4, 8, 16]  # exponential backoff in seconds


class EmbeddingService:
    """
    Service for generating text embeddings via HuggingFace Inference API.

    Implements a singleton pattern to share a single HTTP client.
    Batches requests and retries on 429/503 to handle free-tier limits.

    Attributes:
        model_name: Name of the HuggingFace model being used
        embedding_dim: Dimensionality of the output embeddings (384)
    """

    _instance: Optional["EmbeddingService"] = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the embedding service."""
        self.model_name = settings.embedding_model

    @property
    def embedding_dim(self) -> int:
        """Get the dimensionality of the embeddings."""
        return EMBEDDING_DIM

    async def _call_hf_api(self, texts: List[str]) -> List[List[float]]:
        """
        Call HuggingFace Inference API with exponential backoff retry.

        Handles 429 (rate limit) and 503 (model loading) gracefully.

        Args:
            texts: List of texts to embed (keep ≤5 for free tier)

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If all retries are exhausted
        """
        headers = {
            "Authorization": f"Bearer {settings.hf_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"inputs": texts}

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        HF_API_URL, headers=headers, json=payload
                    )

                    if response.status_code == 200:
                        return response.json()

                    if response.status_code == 429:
                        delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                        logger.warning(
                            f"HF API rate limited (429), retrying in {delay}s "
                            f"(attempt {attempt + 1}/{_MAX_RETRIES})"
                        )
                        await asyncio.sleep(delay)
                        continue

                    if response.status_code == 503:
                        delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                        logger.warning(
                            f"HF model loading (503), retrying in {delay}s "
                            f"(attempt {attempt + 1}/{_MAX_RETRIES})"
                        )
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()

            except httpx.TimeoutException:
                delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                logger.warning(
                    f"HF API timeout, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES})"
                )
                await asyncio.sleep(delay)
                continue

        raise RuntimeError(f"HuggingFace API failed after {_MAX_RETRIES} attempts")

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text with caching.

        Args:
            text: Text to embed

        Returns:
            Embedding as list of floats (384 dimensions)

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

        result = await self._call_hf_api([text])
        embedding = result[0]

        # Cache the result
        if settings.enable_caching:
            from app.services.cache import get_cache_service
            cache = get_cache_service()
            await cache.set_embedding(text, embedding)

        return embedding

    async def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently with caching.

        Processes texts in batches of 5 with a 1s delay between batches
        to respect HuggingFace free-tier rate limits.

        Args:
            texts: List of texts to embed
            show_progress: Whether to log progress (True = log each batch)

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

        results: List[Optional[List[float]]] = [None] * len(texts)
        to_embed: List[str] = []
        to_embed_indices: List[int] = []

        # Check cache for each text
        if settings.enable_caching:
            from app.services.cache import get_cache_service
            cache = get_cache_service()

            for idx, text in enumerate(texts):
                cached = await cache.get_embedding(text)
                if cached is not None:
                    results[idx] = cached
                else:
                    to_embed.append(text)
                    to_embed_indices.append(idx)
        else:
            to_embed = list(texts)
            to_embed_indices = list(range(len(texts)))

        if not to_embed:
            return results  # type: ignore

        logger.info(
            f"Generating {len(to_embed)} embeddings via HuggingFace API "
            f"(batch_size={_BATCH_SIZE})"
        )

        # Split into batches and run up to _CONCURRENT_BATCHES in parallel
        batches = [
            to_embed[i : i + _BATCH_SIZE]
            for i in range(0, len(to_embed), _BATCH_SIZE)
        ]
        num_batches = len(batches)
        if show_progress:
            logger.info(f"Embedding {len(to_embed)} texts in {num_batches} batches ({_CONCURRENT_BATCHES} parallel)")

        semaphore = asyncio.Semaphore(_CONCURRENT_BATCHES)

        async def _embed_batch(batch: List[str], idx: int) -> List[List[float]]:
            async with semaphore:
                if idx > 0 and idx % _CONCURRENT_BATCHES == 0:
                    await asyncio.sleep(_BATCH_DELAY)
                return await self._call_hf_api(batch)

        batch_results = await asyncio.gather(
            *[_embed_batch(batch, i) for i, batch in enumerate(batches)]
        )

        new_embeddings: List[List[float]] = []
        for result in batch_results:
            new_embeddings.extend(result)

        # Store results and cache
        if settings.enable_caching:
            from app.services.cache import get_cache_service
            cache = get_cache_service()

        for text, embedding, orig_idx in zip(to_embed, new_embeddings, to_embed_indices):
            if settings.enable_caching:
                await cache.set_embedding(text, embedding)
            results[orig_idx] = embedding

        logger.info(
            f"Successfully generated {len(new_embeddings)} embeddings "
            f"(dim: {len(new_embeddings[0]) if new_embeddings else 0})"
        )

        return results  # type: ignore

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query.

        For all-MiniLM-L6-v2, queries use the same encoding as documents.

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
            test_embedding = await self.embed_text("test")
            return len(test_embedding) == EMBEDDING_DIM
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False


# Global instance for easy access
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get the global embedding service instance.

    Returns:
        The global EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
