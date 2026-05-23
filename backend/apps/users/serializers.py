"""
User serializers — data validation and representation layer.
Business logic lives in services.py, not here.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extend JWT payload with user role and name.
    Avoids an extra /me API call right after login.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["email"] = self.user.email
        data["full_name"] = self.user.full_name
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Handles new user registration with password confirmation."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "password",
            "password_confirm",
        ]
        read_only_fields = ["id"]

    def validate_role(self, value):
        # Admin accounts cannot be self-registered
        if value == "ADMIN":
            raise serializers.ValidationError("Cannot self-register as admin.")
        return value

    def validate(self, data):
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Read/update profile — never exposes sensitive fields."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "profile_picture",
            "role",
            "is_email_verified",
            "is_online",
            "last_seen",
            "created_at",
        ]
        read_only_fields = ["id", "email", "role", "is_email_verified", "created_at"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        return data


class LogoutSerializer(serializers.Serializer):
    """Accepts the refresh token to blacklist on logout."""

    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    """Step 1: user provides their email to initiate a reset."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Step 2: user provides uidb64, token, and the new password."""

    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return data


class EmailVerificationSerializer(serializers.Serializer):
    """Accepts the email verification token."""

    token = serializers.CharField()
