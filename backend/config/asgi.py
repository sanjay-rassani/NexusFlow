"""
ASGI config for NexusFlow.

Routes HTTP requests to Django and WebSocket connections to Django Channels.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Initialize Django ASGI application early to ensure the app registry is ready
# before importing consumers that depend on models.
django_asgi_app = get_asgi_application()

from config.routing import websocket_urlpatterns  # noqa: E402 — must be after django setup

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
