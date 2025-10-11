"""
Caching system for field mapper.

Provides LRU and TTL caching for expensive operations.
"""
import time
import hashlib
import json
from typing import Any, Optional, Dict
from cachetools import LRUCache, TTLCache
from functools import wraps

from ..config.settings import FieldMapperSettings
from ..config.logging_config import setup_logger

logger = setup_logger(__name__)


class FieldMapperCache:
    """
    Caching system for field mapping operations.

    Provides:
    - LRU cache for frequently accessed data
    - TTL cache for time-sensitive data
    - Cache key generation
    - Hit/miss tracking
    """

    def __init__(self, settings: Optional[FieldMapperSettings] = None):
        """
        Initialize the caching system.

        Args:
            settings: FieldMapperSettings for configuration
        """
        self.settings = settings or FieldMapperSettings()

        # Create LRU cache
        self.lru_cache = LRUCache(maxsize=self.settings.cache_size)

        # Create TTL cache (5 minute TTL)
        self.ttl_cache = TTLCache(maxsize=self.settings.cache_size, ttl=300)

        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

        logger.info(f"FieldMapperCache initialized (size={self.settings.cache_size})")

    def get(self, key: str, use_ttl: bool = False) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            use_ttl: Whether to use TTL cache instead of LRU

        Returns:
            Cached value if found, None otherwise
        """
        cache = self.ttl_cache if use_ttl else self.lru_cache

        if key in cache:
            self.stats["hits"] += 1
            logger.debug(f"Cache HIT: {key}")
            return cache[key]
        else:
            self.stats["misses"] += 1
            logger.debug(f"Cache MISS: {key}")
            return None

    def set(self, key: str, value: Any, use_ttl: bool = False) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            use_ttl: Whether to use TTL cache instead of LRU
        """
        cache = self.ttl_cache if use_ttl else self.lru_cache
        cache[key] = value
        logger.debug(f"Cache SET: {key}")

    def clear(self) -> None:
        """Clear all caches."""
        self.lru_cache.clear()
        self.ttl_cache.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.2f}%",
            "lru_size": len(self.lru_cache),
            "ttl_size": len(self.ttl_cache),
        }

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        Generate a cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            MD5 hash of the arguments
        """
        # Create a stable representation
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }

        # Convert to JSON and hash
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()

        return key_hash


# Global cache instance
_cache_instance: Optional[FieldMapperCache] = None


def get_cache() -> FieldMapperCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = FieldMapperCache()
    return _cache_instance


def cached(use_ttl: bool = False):
    """
    Decorator for caching function results.

    Args:
        use_ttl: Whether to use TTL cache instead of LRU

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key
            cache_key = FieldMapperCache.generate_key(func.__name__, *args, **kwargs)

            # Try to get from cache
            result = cache.get(cache_key, use_ttl=use_ttl)

            if result is not None:
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, use_ttl=use_ttl)

            return result

        return wrapper
    return decorator
