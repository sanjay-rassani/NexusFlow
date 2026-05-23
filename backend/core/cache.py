"""
Cache utility helpers.
Full Redis caching strategy implemented in Phase 6.
"""

from django.core.cache import cache


def make_cache_key(*parts: str) -> str:
    """Build a namespaced cache key from parts."""
    return ":".join(str(p) for p in parts)


def get_or_set(key: str, callback, timeout: int = 300):
    """
    Return cached value if it exists, otherwise compute and cache it.

    Args:
        key: Cache key (use make_cache_key for namespacing)
        callback: Zero-arg callable that returns the value to cache
        timeout: TTL in seconds (default 5 minutes)
    """
    value = cache.get(key)
    if value is None:
        value = callback()
        cache.set(key, value, timeout)
    return value


def invalidate_pattern(prefix: str) -> None:
    """
    Delete all cache keys with a given prefix.
    Requires Redis backend (uses scan_iter).
    """
    from django_redis import get_redis_connection

    conn = get_redis_connection("default")
    pattern = f"*nexusflow:{prefix}*"
    keys = conn.keys(pattern)
    if keys:
        conn.delete(*keys)
