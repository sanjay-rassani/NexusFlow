"""
Development settings — extends base with debug tooling.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# ──────────────────────────────────────────────
# Debug Toolbar (optional, enabled in dev)
# ──────────────────────────────────────────────
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# ──────────────────────────────────────────────
# Relax JWT token lifetimes for easier dev testing
# ──────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {  # noqa: F405
    **SIMPLE_JWT,  # noqa: F405
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

# ──────────────────────────────────────────────
# Show all SQL in console during dev
# ──────────────────────────────────────────────
# LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"  # noqa: F405
