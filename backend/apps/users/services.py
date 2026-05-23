"""
User business logic service layer.
Views call services; services call models. Never reverse this.
"""

import logging
from django.contrib.auth import authenticate
from django.utils import timezone

from .models import User

logger = logging.getLogger(__name__)


class UserService:

    @staticmethod
    def register_user(validated_data: dict) -> User:
        """Create and return a new user."""
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone_number=validated_data.get("phone_number"),
            role=validated_data.get("role", "CUSTOMER"),
            password=validated_data["password"],
        )
        logger.info("New user registered: %s (role=%s)", user.email, user.role)
        return user

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> None:
        """Validate old password and set new one."""
        if not user.check_password(old_password):
            from rest_framework import serializers
            raise serializers.ValidationError({"old_password": "Incorrect password."})
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        logger.info("Password changed for user: %s", user.email)

    @staticmethod
    def mark_user_online(user: User) -> None:
        User.objects.filter(pk=user.pk).update(is_online=True)

    @staticmethod
    def mark_user_offline(user: User) -> None:
        User.objects.filter(pk=user.pk).update(is_online=False, last_seen=timezone.now())
