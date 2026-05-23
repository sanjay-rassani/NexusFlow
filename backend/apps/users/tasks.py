"""
Celery tasks for the users app.
All email sending is async — never block the request/response cycle.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # retry after 60s
    name="users.send_password_reset_email",
)
def send_password_reset_email(self, user_email: str, user_name: str, reset_url: str) -> None:
    """
    Sends a password reset email asynchronously.
    Retries up to 3 times with a 60s delay on failure.
    """
    subject = "Reset your NexusFlow password"
    message = (
        f"Hi {user_name},\n\n"
        f"You requested a password reset for your NexusFlow account.\n\n"
        f"Click the link below to set a new password:\n{reset_url}\n\n"
        f"This link expires in 1 hour.\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"— The NexusFlow Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info("Password reset email sent to %s", user_email)
    except Exception as exc:
        logger.error("Failed to send password reset email to %s: %s", user_email, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="users.send_email_verification",
)
def send_email_verification(self, user_email: str, user_name: str, verify_url: str) -> None:
    """
    Sends an email verification link asynchronously.
    """
    subject = "Verify your NexusFlow email address"
    message = (
        f"Hi {user_name},\n\n"
        f"Welcome to NexusFlow! Please verify your email address to activate your account.\n\n"
        f"Verify email: {verify_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"— The NexusFlow Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info("Verification email sent to %s", user_email)
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", user_email, exc)
        raise self.retry(exc=exc)


@shared_task(name="users.send_welcome_email")
def send_welcome_email(user_email: str, user_name: str) -> None:
    """
    Sent after successful email verification.
    Fire-and-forget — no retries needed for welcome emails.
    """
    subject = "Welcome to NexusFlow!"
    message = (
        f"Hi {user_name},\n\n"
        f"Your email has been verified. Your account is now active.\n\n"
        f"— The NexusFlow Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.warning("Failed to send welcome email to %s: %s", user_email, exc)
