"""
Token generators for email verification and password reset.

Design:
  - Password reset uses Django's PasswordResetTokenGenerator.
    The token includes a hash of the user's password, so it is
    automatically invalidated once the password is changed.

  - Email verification uses a UUID stored in Redis with a 24-hour TTL.
    This avoids database writes and is trivially revocable (just delete the key).
"""

import uuid
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode


# ──────────────────────────────────────────────
# Password Reset
# ──────────────────────────────────────────────

class NexusFlowPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """
    Extends Django's built-in generator.
    Token is invalidated after use because Django hashes last_login + password
    into the token — changing the password changes both, breaking old tokens.
    """
    pass


password_reset_token_generator = NexusFlowPasswordResetTokenGenerator()


def make_password_reset_token(user) -> tuple[str, str]:
    """
    Returns (uidb64, token) to be embedded in a reset URL.
    Example URL: /reset-password/{uidb64}/{token}/
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = password_reset_token_generator.make_token(user)
    return uidb64, token


def verify_password_reset_token(uidb64: str, token: str):
    """
    Returns the User if (uidb64, token) is valid, otherwise None.
    """
    from apps.users.models import User

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None

    if password_reset_token_generator.check_token(user, token):
        return user
    return None


# ──────────────────────────────────────────────
# Email Verification
# ──────────────────────────────────────────────

_EMAIL_VERIFY_PREFIX = "email_verify"
_EMAIL_VERIFY_TTL = 60 * 60 * 24  # 24 hours


def make_email_verification_token(user) -> str:
    """
    Generates a UUID token, stores user.pk in Redis for 24h, and returns the token.
    """
    token = str(uuid.uuid4())
    cache_key = f"{_EMAIL_VERIFY_PREFIX}:{token}"
    cache.set(cache_key, str(user.pk), timeout=_EMAIL_VERIFY_TTL)
    return token


def verify_email_verification_token(token: str):
    """
    Returns the User if the token exists in Redis, otherwise None.
    Deletes the token on first successful use (one-time-use).
    """
    from apps.users.models import User

    cache_key = f"{_EMAIL_VERIFY_PREFIX}:{token}"
    user_pk = cache.get(cache_key)

    if not user_pk:
        return None

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return None

    cache.delete(cache_key)
    return user
