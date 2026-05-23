"""
User views — thin controllers that delegate to services.
No business logic here; only HTTP concerns (auth, permissions, response shaping).
"""

import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    EmailVerificationSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from .services import UserService

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Open endpoint. Sends verification email on success.
    """

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserService.register_user(serializer.validated_data)
        return Response(
            {
                **UserProfileSerializer(user).data,
                "detail": "Account created. Please check your email to verify your account.",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Returns access + refresh JWT with role and full_name in payload.
    """

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the provided refresh token, invalidating the session.
    The client must also discard the access token locally.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError as exc:
            return Response(
                {"error": True, "code": "INVALID_TOKEN", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        UserService.mark_user_offline(request.user)
        logger.info("User logged out: %s", request.user.email)
        return Response({"detail": "Logged out successfully."})


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/auth/me/ — authenticated user's profile."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        UserService.change_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
        )
        return Response({"detail": "Password updated successfully."})


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset/
    Step 1: user submits their email to receive a reset link.
    Always returns 200 regardless of whether the email exists (prevents enumeration).
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        UserService.request_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "If that email is registered, a password reset link has been sent."}
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password-reset/confirm/
    Step 2: user submits uidb64 + token + new password.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            UserService.confirm_password_reset(
                uidb64=serializer.validated_data["uidb64"],
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValueError as exc:
            return Response(
                {"error": True, "code": "INVALID_TOKEN", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"detail": "Password has been reset. You can now log in."})


class EmailVerifySendView(APIView):
    """
    POST /api/v1/auth/email/verify/send/
    Re-sends a verification email to the current authenticated user.
    Useful if the original email was missed.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.is_email_verified:
            return Response(
                {"detail": "Your email is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        UserService.send_verification_email(request.user)
        return Response({"detail": "Verification email sent. Please check your inbox."})


class EmailVerifyConfirmView(APIView):
    """
    POST /api/v1/auth/email/verify/confirm/
    Accepts the token from the verification link and marks email as verified.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = UserService.verify_email(serializer.validated_data["token"])
        except ValueError as exc:
            return Response(
                {"error": True, "code": "INVALID_TOKEN", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "Email verified successfully.",
                "email": user.email,
            }
        )
