"""
ASGI config for NexusFlow.

Routes:
  - HTTP  → Django ASGI application (REST API, admin, static)
  - WebSocket → Django Channels with JWT authentication middleware

WebSocket auth flow:
  Client connects: ws://host/ws/.../?token=<jwt_access_token>
  JWTAuthMiddleware extracts + validates the token and sets scope["user"].
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Initialize Django ASGI first so the app registry is ready before consumers are imported
django_asgi_app = get_asgi_application()

from config.routing import websocket_urlpatterns  # noqa: E402
from core.middleware import JWTAuthMiddlewareStack  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            )
        ),
    }
)
