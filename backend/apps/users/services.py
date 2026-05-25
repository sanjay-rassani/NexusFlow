"""
User business logic service layer.
Views call services; services call models. Never reverse this.
"""

import logging

from django.conf import settings
from django.utils import timezone

from .models import User

logger = logging.getLogger(__name__)


class UserService:

    @staticmethod
    def register_user(validated_data: dict) -> User:
        """Create and return a new user, then dispatch verification email."""
        email = validated_data["email"]
        # username is not used for login (email is the USERNAME_FIELD) but
        # AbstractUser still requires the field. Use the email prefix as a
        # non-unique identifier — the uniqueness constraint was dropped in
        # migration 0002_remove_username_unique_constraint.
        username = email.split("@")[0]

        user = User.objects.create_user(
            email=email,
            username=username,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone_number=validated_data.get("phone_number"),
            role=validated_data.get("role", "CUSTOMER"),
            password=validated_data["password"],
        )
        logger.info("New user registered: %s (role=%s)", user.email, user.role)
        UserService.send_verification_email(user)
        return user

    @staticmethod
    def send_verification_email(user: User) -> None:
        """Generate an email verification token and queue the email task."""
        from .tokens import make_email_verification_token
        from .tasks import send_email_verification

        token = make_email_verification_token(user)
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        verify_url = f"{frontend_url}/verify-email?token={token}"

        send_email_verification.delay(
            user_email=user.email,
            user_name=user.full_name or user.username,
            verify_url=verify_url,
        )
        logger.info("Verification email queued for %s", user.email)

    @staticmethod
    def verify_email(token: str) -> User:
        """
        Validate the token, mark the user as verified.
        Raises ValueError on invalid/expired token.
        """
        from .tokens import verify_email_verification_token
        from .tasks import send_welcome_email

        user = verify_email_verification_token(token)
        if not user:
            raise ValueError("Invalid or expired verification token.")

        if user.is_email_verified:
            return user  # idempotent

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified", "updated_at"])

        send_welcome_email.delay(
            user_email=user.email,
            user_name=user.full_name or user.username,
        )
        logger.info("Email verified for user: %s", user.email)
        return user

    @staticmethod
    def request_password_reset(email: str) -> None:
        """
        Generate a password reset token and email it.
        Always returns success even if email doesn't exist (prevents enumeration).
        """
        from .tokens import make_password_reset_token
        from .tasks import send_password_reset_email

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            logger.warning("Password reset requested for unknown email: %s", email)
            return  # Silent — don't leak whether the email exists

        uidb64, token = make_password_reset_token(user)
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password/{uidb64}/{token}"

        send_password_reset_email.delay(
            user_email=user.email,
            user_name=user.full_name or user.username,
            reset_url=reset_url,
        )
        logger.info("Password reset email queued for %s", user.email)

    @staticmethod
    def confirm_password_reset(uidb64: str, token: str, new_password: str) -> User:
        """
        Validate the token and set a new password.
        Raises ValueError on invalid/expired token.
        """
        from .tokens import verify_password_reset_token

        user = verify_password_reset_token(uidb64, token)
        if not user:
            raise ValueError("Invalid or expired password reset token.")

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        logger.info("Password reset successful for user: %s", user.email)
        return user

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> None:
        """Validate old password and set the new one (authenticated user)."""
        if not user.check_password(old_password):
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({"old_password": "Incorrect password."})
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        logger.info("Password changed for user: %s", user.email)

    @staticmethod
    def mark_user_online(user: User) -> None:
        User.objects.filter(pk=user.pk).update(is_online=True)

    @staticmethod
    def mark_user_offline(user: User) -> None:
        User.objects.filter(pk=user.pk).update(
            is_online=False, last_seen=timezone.now()
        )
