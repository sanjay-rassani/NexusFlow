"""
Redis-based rate limiter for DRF API views.

Algorithm: Fixed window counter.
  - On each request, INCR a Redis key scoped to (prefix, client_ip).
  - On first request, SET the key's expiry to window_seconds.
  - If the counter exceeds max_requests, return HTTP 429.

Why not use django-ratelimit?
  - Adding a dependency for ~20 lines of Redis logic is unnecessary.
  - This implementation is transparent, testable, and already uses our
    existing Redis connection pool.

Usage (method decorator on DRF APIView/GenericAPIView):

    from core.rate_limit import rate_limit

    class LoginView(TokenObtainPairView):
        @rate_limit(prefix="login", max_requests=10, window_seconds=60)
        def post(self, request, *args, **kwargs):
            ...

    class RegisterView(generics.CreateAPIView):
        @rate_limit(prefix="register", max_requests=5, window_seconds=60)
        def create(self, request, *args, **kwargs):
            ...
"""

import functools
import logging

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _get_client_ip(request) -> str:
    """
    Extract the real client IP, respecting X-Forwarded-For from Nginx.
    Falls back to REMOTE_ADDR if the header is absent.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _check_rate_limit(prefix: str, client_ip: str, max_requests: int, window_seconds: int) -> tuple[bool, int, int]:
    """
    Increments the request counter and returns (allowed, current_count, limit).
    Uses direct Redis connection for atomic INCR + EXPIRE.
    """
    from django_redis import get_redis_connection

    key = f"ratelimit:{prefix}:{client_ip}"
    conn = get_redis_connection("default")

    try:
        current = conn.incr(key)
        if current == 1:
            # First request in this window — set the expiry
            conn.expire(key, window_seconds)
        return current <= max_requests, current, max_requests
    except Exception as exc:
        # Redis unavailable — fail open (allow the request) and log
        logger.error("Rate limit Redis error for key '%s': %s", key, exc)
        return True, 0, max_requests


def rate_limit(prefix: str, max_requests: int = 10, window_seconds: int = 60):
    """
    Decorator factory for rate-limiting DRF view methods.

    Args:
        prefix:         Namespace for the Redis key (e.g. "login", "register").
        max_requests:   Maximum allowed requests in the window.
        window_seconds: Duration of the rate-limit window in seconds.
    """
    def decorator(view_method):
        @functools.wraps(view_method)
        def wrapper(self, request, *args, **kwargs):
            client_ip = _get_client_ip(request)
            allowed, current, limit = _check_rate_limit(
                prefix, client_ip, max_requests, window_seconds
            )

            if not allowed:
                logger.warning(
                    "Rate limit exceeded: prefix=%s ip=%s count=%d limit=%d",
                    prefix,
                    client_ip,
                    current,
                    limit,
                )
                return Response(
                    {
                        "error": True,
                        "code": "RATE_LIMITED",
                        "message": (
                            f"Too many requests. "
                            f"Limit is {limit} per {window_seconds}s. "
                            f"Please wait and try again."
                        ),
                        "details": {
                            "limit": limit,
                            "window_seconds": window_seconds,
                            "current": current,
                        },
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            return view_method(self, request, *args, **kwargs)

        return wrapper
    return decorator
