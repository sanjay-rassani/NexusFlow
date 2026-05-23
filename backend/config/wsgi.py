"""
WSGI config for NexusFlow.
Used by gunicorn for serving HTTP in production (non-WebSocket).
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()
