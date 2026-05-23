"""
WebSocket JWT Authentication Middleware.

Problem: Django's AuthMiddlewareStack only works with session-based auth.
JWT tokens cannot be sent as Authorization headers in browser WebSocket connections.

Solution:
  Clients pass the JWT access token as a query parameter:
    ws://host/ws/orders/123/?token=<access_token>

  This middleware:
    1. Extracts the token from the query string
    2. Validates it with simplejwt
    3. Loads the User and sets scope["user"]
    4. Falls back to AnonymousUser on any failure (consumers must check authentication)

Usage in consumers:
    if not self.scope["user"].is_authenticated:
        await self.close(code=4001)  # Unauthorized
"""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_str: str):
    """
    Validates the JWT access token and returns the associated User.
    Returns AnonymousUser on any validation failure.
    Database call is run in a thread pool via database_sync_to_async.
    """
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token_str)
        user = jwt_auth.get_user(validated_token)
        return user
    except (InvalidToken, TokenError) as exc:
        logger.debug("WebSocket JWT validation failed: %s", exc)
        return AnonymousUser()
    except Exception as exc:
        logger.warning("Unexpected error during WebSocket JWT auth: %s", exc)
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Channels middleware that populates scope["user"] from a JWT query param.
    Must wrap the URLRouter (not the entire ProtocolTypeRouter).
    """

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            query_string = scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token_list = params.get("token", [])

            if token_list:
                scope["user"] = await get_user_from_token(token_list[0])
            else:
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Convenience wrapper — use this in asgi.py instead of AuthMiddlewareStack.

    Example:
        application = ProtocolTypeRouter({
            "websocket": JWTAuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            ),
        })
    """
    return JWTAuthMiddleware(inner)
