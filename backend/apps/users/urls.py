from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    ChangePasswordView,
    EmailVerifyConfirmView,
    EmailVerifySendView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)

urlpatterns = [
    # ── Registration & Login ──────────────────
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),

    # ── Token Management ──────────────────────
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),

    # ── Profile ───────────────────────────────
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),

    # ── Password Reset ────────────────────────
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),

    # ── Email Verification ────────────────────
    path("email/verify/send/", EmailVerifySendView.as_view(), name="email-verify-send"),
    path("email/verify/confirm/", EmailVerifyConfirmView.as_view(), name="email-verify-confirm"),
]
