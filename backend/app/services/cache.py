"""
Redis-based caching service for embeddings and query responses.
"""

import logging
import json
import hashlib
from typing import Optional, List, Dict, Any
from redis.asyncio import Redis
from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Async Redis cache for embeddings and responses."""

    def __init__(self):
        self.redis_url = settings.redis_url
        self._client: Optional[Redis] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "embedding_hits": 0,
            "embedding_misses": 0,
            "response_hits": 0,
            "response_misses": 0,
        }

    async def _get_client(self) -> Redis:
        """Lazy initialize Redis connection."""
        if self._client is None:
            try:
                self._client = await Redis.from_url(
                    self.redis_url,
                    decode_responses=False,  # We'll handle encoding
                    socket_connect_timeout=5
                )
                await self._client.ping()
                logger.info(f"✓ Redis connected: {self.redis_url}")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                raise
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

            client = await self._get_client()
            key = f"embed:{self._hash_key(text)}"
            cached = await client.get(key)

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
            client = await self._get_client()
            key = f"embed:{self._hash_key(text)}"
            await client.setex(
                key,
                settings.cache_ttl_embeddings,
                json.dumps(embedding)
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

            client = await self._get_client()
            key = f"query:{self._hash_key(question)}"
            cached = await client.get(key)

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
            client = await self._get_client()
            key = f"query:{self._hash_key(question)}"
            data = {
                "answer": answer,
                "sources": sources,
                "cached_at": __import__("time").time()
            }
            await client.setex(
                key,
                settings.cache_ttl_responses,
                json.dumps(data)
            )
            logger.debug(f"Cached response: {key[:20]}...")
        except Exception as e:
            logger.warning(f"Cache set_response error: {e}")

    async def check_health(self) -> bool:
        """Check Redis connectivity."""
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
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
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")


# Global instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Factory function for cache service."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
