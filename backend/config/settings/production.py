"""
Production settings — security-hardened, performance-optimized.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# ──────────────────────────────────────────────
# Security Headers
# ──────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# ──────────────────────────────────────────────
# Sentry Error Tracking (optional)
# ──────────────────────────────────────────────
import environ

env = environ.Env()
SENTRY_DSN = env("SENTRY_DSN", default=None)

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# ──────────────────────────────────────────────
# Logging — structured file logging in production
# ──────────────────────────────────────────────
LOGGING["handlers"]["file"] = {  # noqa: F405
    "class": "logging.handlers.RotatingFileHandler",
    "filename": "/var/log/nexusflow/app.log",
    "maxBytes": 1024 * 1024 * 50,  # 50 MB
    "backupCount": 5,
    "formatter": "verbose",
}
LOGGING["root"]["handlers"] = ["console", "file"]  # noqa: F405
