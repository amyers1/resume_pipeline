"""
Redis-based caching utilities for resume pipeline.

This replaces the file-based cache with a distributed Redis cache
that can be shared across multiple workers.
"""

import json
import logging
from typing import Optional

import redis
from redis.exceptions import RedisError

from resume_pipeline.models import CachedPipelineState

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """
    Manages pipeline state caching using Redis.

    Provides a distributed cache that can be shared across multiple
    workers, replacing the file-based cache that only works on a
    single machine.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ttl_days: int = 30,
        key_prefix: str = "resume:cache:",
    ):
        """
        Initialize Redis cache manager.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (if required)
            ttl_days: Time-to-live for cached items in days
            key_prefix: Prefix for all cache keys
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ttl_seconds = ttl_days * 24 * 60 * 60
        self.key_prefix = key_prefix

        # Initialize Redis client
        self._redis: Optional[redis.Redis] = None
        self._connect()

    def _connect(self) -> bool:
        """
        Connect to Redis server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,  # Auto-decode bytes to strings
                socket_timeout=5,
                socket_connect_timeout=5,
            )

            # Test connection
            self._redis.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
            return True

        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._redis = None
            return False

    def _get_full_key(self, cache_key: str) -> str:
        """Get full Redis key with prefix."""
        return f"{self.key_prefix}{cache_key}"

    def save(self, cache_key: str, state: CachedPipelineState) -> bool:
        """
        Save pipeline state to Redis cache.

        Args:
            cache_key: Unique cache key (hash of job + career profile)
            state: Pipeline state to cache

        Returns:
            True if save successful, False otherwise
        """
        if not self._redis:
            logger.warning("Redis not connected, cannot save to cache")
            return False

        try:
            full_key = self._get_full_key(cache_key)

            # Serialize state to JSON
            json_data = state.model_dump_json()

            # Save with TTL
            self._redis.setex(
                name=full_key,
                time=self.ttl_seconds,
                value=json_data,
            )

            print(f"  ✓ Saved to Redis cache: {cache_key[:8]}...")
            logger.debug(f"Cached state saved: {full_key}")
            return True

        except RedisError as e:
            logger.error(f"Failed to save to cache: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving to cache: {e}")
            return False

    def load(self, cache_key: str) -> Optional[CachedPipelineState]:
        """
        Load pipeline state from Redis cache.

        Args:
            cache_key: Unique cache key

        Returns:
            Cached state if found and valid, None otherwise
        """
        if not self._redis:
            logger.warning("Redis not connected, cannot load from cache")
            return None

        try:
            full_key = self._get_full_key(cache_key)

            # Get from Redis
            json_data = self._redis.get(full_key)

            if json_data is None:
                logger.debug(f"Cache miss: {full_key}")
                return None

            # Deserialize from JSON
            cached = CachedPipelineState.model_validate_json(json_data)

            print(f"  ✓ Loaded from Redis cache: {cache_key[:8]}...")
            logger.debug(f"Cache hit: {full_key}")
            return cached

        except RedisError as e:
            logger.error(f"Failed to load from cache: {e}")
            return None
        except Exception as e:
            logger.error(f"Cache read failed: {e}")
            return None

    def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cached states.

        Args:
            pattern: Optional pattern to match keys (e.g., "abc*")
                    If None, clears all resume cache keys

        Returns:
            Number of keys deleted
        """
        if not self._redis:
            logger.warning("Redis not connected, cannot clear cache")
            return 0

        try:
            # Build search pattern
            if pattern:
                search_pattern = f"{self.key_prefix}{pattern}"
            else:
                search_pattern = f"{self.key_prefix}*"

            # Find matching keys
            keys = list(self._redis.scan_iter(match=search_pattern, count=100))

            if not keys:
                print("  ℹ No cache entries to clear")
                return 0

            # Delete keys
            deleted = self._redis.delete(*keys)
            print(f"  ✓ Cleared {deleted} cache entries")
            logger.info(f"Cleared {deleted} cache entries matching {search_pattern}")
            return deleted

        except RedisError as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

    def exists(self, cache_key: str) -> bool:
        """
        Check if a cache key exists.

        Args:
            cache_key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        if not self._redis:
            return False

        try:
            full_key = self._get_full_key(cache_key)
            return bool(self._redis.exists(full_key))
        except RedisError:
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self._redis:
            return {
                "connected": False,
                "total_keys": 0,
                "memory_used": "0B",
            }

        try:
            # Count resume cache keys
            pattern = f"{self.key_prefix}*"
            total_keys = sum(1 for _ in self._redis.scan_iter(match=pattern, count=100))

            # Get Redis memory stats
            info = self._redis.info("memory")
            memory_used = info.get("used_memory_human", "Unknown")

            return {
                "connected": True,
                "total_keys": total_keys,
                "memory_used": memory_used,
                "redis_version": self._redis.info("server").get(
                    "redis_version", "Unknown"
                ),
            }

        except RedisError as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "connected": False,
                "error": str(e),
            }

    def healthcheck(self) -> bool:
        """
        Check if Redis is healthy.

        Returns:
            True if Redis is responding, False otherwise
        """
        if not self._redis:
            return False

        try:
            return self._redis.ping()
        except RedisError:
            return False

    def close(self):
        """Close Redis connection."""
        if self._redis:
            try:
                self._redis.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._redis = None


# Backwards compatibility: provide both names
CacheManager = RedisCacheManager
