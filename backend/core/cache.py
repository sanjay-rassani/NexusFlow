"""
Redis caching layer for NexusFlow.

Strategy:
  - Cache public READ-heavy endpoints: vendor list, vendor detail, product list.
  - Skip caching for authenticated/personalized endpoints (orders, me, admin).
  - Invalidate proactively on any write — never serve stale data past TTL.

Key format (handled by django_redis internally):
    {KEY_PREFIX}:{VERSION}:{our_key}
    e.g.  nexusflow:1:vendors:list:page=1&page_size=20

Cache DB: Redis DB 0 (same as general cache — see settings/base.py)

Invalidation:
    - Pattern-based via redis SCAN (delete_pattern from django_redis)
    - Fine-grained per-object keys for detail views
    - All vendor-level keys wiped when vendor metadata changes
    - All product keys for a vendor wiped when any product in that vendor changes
"""

import hashlib
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# TTL constants (seconds)
# ──────────────────────────────────────────────
TTL_VENDOR_LIST = 60 * 5       # 5 min  — refreshed frequently enough
TTL_VENDOR_DETAIL = 60 * 10    # 10 min — less volatile than list
TTL_PRODUCT_LIST = 60 * 5      # 5 min
TTL_USER_SESSION = 60 * 60     # 1 hour — used for lightweight user data caching


# ──────────────────────────────────────────────
# Cache key builders
# ──────────────────────────────────────────────

def _param_hash(query_params) -> str:
    """
    Produces a short stable hash from a QueryDict (or dict) of query params.
    Sorting ensures ?name=x&is_open=true == ?is_open=true&name=x.
    """
    sorted_params = "&".join(
        f"{k}={v}" for k, v in sorted(query_params.items())
    )
    return hashlib.md5(sorted_params.encode()).hexdigest()[:12]


class CacheKeys:
    """Centralised cache key namespace — prevents typo-based key mismatches."""

    @staticmethod
    def vendor_list(query_params=None) -> str:
        suffix = _param_hash(query_params) if query_params else "default"
        return f"vendors:list:{suffix}"

    @staticmethod
    def vendor_detail(vendor_id) -> str:
        return f"vendors:detail:{vendor_id}"

    @staticmethod
    def vendor_products(vendor_id, query_params=None) -> str:
        suffix = _param_hash(query_params) if query_params else "default"
        return f"vendors:{vendor_id}:products:{suffix}"

    @staticmethod
    def product_detail(product_id) -> str:
        return f"products:detail:{product_id}"


# ──────────────────────────────────────────────
# Generic helpers
# ──────────────────────────────────────────────

def get_or_set(key: str, callback, timeout: int = 300):
    """
    Return cached value if it exists, otherwise compute and cache it.

    Args:
        key:      Cache key string (from CacheKeys.*).
        callback: Zero-arg callable that produces the value to cache.
        timeout:  TTL in seconds.
    """
    value = cache.get(key)
    if value is not None:
        logger.debug("Cache HIT: %s", key)
        return value

    logger.debug("Cache MISS: %s", key)
    value = callback()
    cache.set(key, value, timeout)
    return value


def invalidate(*keys: str) -> None:
    """Delete one or more exact cache keys."""
    for key in keys:
        cache.delete(key)
        logger.debug("Cache INVALIDATED: %s", key)


def invalidate_pattern(pattern: str) -> None:
    """
    Delete all keys matching a glob pattern.
    Uses django_redis's SCAN-based delete_pattern — safe on large keyspaces
    (unlike KEYS which blocks Redis).

    Pattern examples:
        "vendors:list:*"        — all vendor list pages
        "vendors:5:products:*"  — all product list pages for vendor 5
    """
    try:
        cache.delete_pattern(f"*{pattern}*")
        logger.debug("Cache INVALIDATED pattern: *%s*", pattern)
    except Exception as exc:
        # delete_pattern is django_redis-specific; degrade gracefully on other backends
        logger.warning("Cache pattern invalidation failed: %s", exc)


# ──────────────────────────────────────────────
# Domain-specific invalidation helpers
# Called by service layer on every write operation
# ──────────────────────────────────────────────

def invalidate_vendor_cache(vendor_id=None) -> None:
    """
    Wipe all cached data related to a vendor.
    Called when: vendor is created, updated, activated/deactivated, opened/closed.
    """
    invalidate_pattern("vendors:list:")          # all list pages
    if vendor_id is not None:
        invalidate(CacheKeys.vendor_detail(vendor_id))
        invalidate_pattern(f"vendors:{vendor_id}:products:")
    logger.info("Vendor cache invalidated (vendor_id=%s)", vendor_id)


def invalidate_product_cache(vendor_id, product_id=None) -> None:
    """
    Wipe product list cache for a specific vendor.
    Called when: product is created, updated, soft-deleted.
    """
    invalidate_pattern(f"vendors:{vendor_id}:products:")
    if product_id is not None:
        invalidate(CacheKeys.product_detail(product_id))
    # Also invalidate vendor detail (product_count embedded there)
    invalidate(CacheKeys.vendor_detail(vendor_id))
    logger.info("Product cache invalidated (vendor_id=%s, product_id=%s)", vendor_id, product_id)
