"""
Upstash Redis-based caching service for embeddings and query responses.

Uses the Upstash Redis HTTP REST client instead of TCP-based redis-py,
making it compatible with serverless environments like Railway.
"""

import logging
import json
import hashlib
import asyncio
from typing import Optional, List, Dict, Any
from upstash_redis import Redis

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Upstash Redis cache for embeddings and responses (HTTP-based)."""

    def __init__(self):
        self._client: Optional[Redis] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "embedding_hits": 0,
            "embedding_misses": 0,
            "response_hits": 0,
            "response_misses": 0,
        }

    def _get_client(self) -> Redis:
        """Lazy initialize Upstash Redis HTTP client."""
        if self._client is None:
            self._client = Redis(
                url=settings.upstash_redis_rest_url,
                token=settings.upstash_redis_rest_token,
            )
            logger.info("✓ Upstash Redis client initialized")
        return self._client

    def _hash_key(self, text: str) -> str:
        """Create deterministic hash for cache key."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding by text hash."""
        if not settings.enable_caching:
            return None

        try:
            from app.services.metrics import cache_hit_counter, cache_miss_counter

            client = self._get_client()
            key = f"embed:{self._hash_key(text)}"
            cached = await asyncio.to_thread(client.get, key)

            if cached:
                self._stats["embedding_hits"] += 1
                self._stats["hits"] += 1
                cache_hit_counter.labels(cache_type="embedding").inc()
                logger.debug(f"Cache HIT: embedding for text hash {key[:20]}...")
                return json.loads(cached)

            self._stats["embedding_misses"] += 1
            self._stats["misses"] += 1
            cache_miss_counter.labels(cache_type="embedding").inc()
            return None
        except Exception as e:
            logger.warning(f"Cache get_embedding error: {e}")
            return None

    async def set_embedding(self, text: str, embedding: List[float]):
        """Cache embedding with TTL."""
        if not settings.enable_caching:
            return

        try:
            client = self._get_client()
            key = f"embed:{self._hash_key(text)}"
            await asyncio.to_thread(
                client.set, key, json.dumps(embedding), ex=settings.cache_ttl_embeddings
            )
            logger.debug(f"Cached embedding: {key[:20]}...")
        except Exception as e:
            logger.warning(f"Cache set_embedding error: {e}")

    async def get_response(self, question: str) -> Optional[Dict[str, Any]]:
        """Get cached query response."""
        if not settings.enable_caching:
            return None

        try:
            from app.services.metrics import cache_hit_counter, cache_miss_counter

            client = self._get_client()
            key = f"query:{self._hash_key(question)}"
            cached = await asyncio.to_thread(client.get, key)

            if cached:
                self._stats["response_hits"] += 1
                self._stats["hits"] += 1
                cache_hit_counter.labels(cache_type="response").inc()
                logger.info(f"Cache HIT: response for query hash {key[:20]}...")
                return json.loads(cached)

            self._stats["response_misses"] += 1
            self._stats["misses"] += 1
            cache_miss_counter.labels(cache_type="response").inc()
            return None
        except Exception as e:
            logger.warning(f"Cache get_response error: {e}")
            return None

    async def set_response(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]]
    ):
        """Cache query response with TTL."""
        if not settings.enable_caching:
            return

        try:
            client = self._get_client()
            key = f"query:{self._hash_key(question)}"
            data = {
                "answer": answer,
                "sources": sources,
                "cached_at": __import__("time").time()
            }
            await asyncio.to_thread(
                client.set, key, json.dumps(data), ex=settings.cache_ttl_responses
            )
            logger.debug(f"Cached response: {key[:20]}...")
        except Exception as e:
            logger.warning(f"Cache set_response error: {e}")

    async def check_health(self) -> bool:
        """Check Upstash Redis connectivity."""
        try:
            client = self._get_client()
            await asyncio.to_thread(client.ping)
            return True
        except Exception as e:
            logger.error(f"Upstash Redis health check failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            "hit_rate": round(hit_rate, 3),
            "total_hits": self._stats["hits"],
            "total_misses": self._stats["misses"],
            "embedding_hits": self._stats["embedding_hits"],
            "embedding_misses": self._stats["embedding_misses"],
            "response_hits": self._stats["response_hits"],
            "response_misses": self._stats["response_misses"],
        }

    async def close(self):
        """No-op: Upstash Redis is HTTP-based, no persistent connection to close."""
        logger.info("Upstash Redis client closed (no-op, HTTP-based)")


# Global instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Factory function for cache service."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
