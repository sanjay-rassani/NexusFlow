"""
Custom User model with role-based access control.

Design decisions:
- Single User table with a `role` field (not separate models per role) keeps
  queries simple and avoids complex joins for auth checks.
- AbstractUser gives us all Django auth features for free.
- `phone_number` is nullable — required for riders/vendors, optional for customers.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Customer"
    VENDOR = "VENDOR", "Vendor"
    RIDER = "RIDER", "Delivery Rider"
    ADMIN = "ADMIN", "Admin"


class User(AbstractUser):
    """
    Extended user model with roles and profile fields.
    email is the login credential; username is unused but kept as a nullable,
    non-unique field to remain compatible with third-party packages that
    reference AbstractUser.username.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Override AbstractUser.username — we don't use it, but some third-party packages
    # (e.g. DRF, rest_framework_simplejwt) may reference it. Remove the unique constraint
    # to prevent IntegrityError when multiple users are created without an explicit username.
    username = models.CharField(max_length=150, blank=True, default="")
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profiles/", blank=True, null=True
    )
    is_email_verified = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)  # Tracked via WebSocket presence
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use email as the login identifier instead of username
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_customer(self):
        return self.role == UserRole.CUSTOMER

    @property
    def is_vendor(self):
        return self.role == UserRole.VENDOR

    @property
    def is_rider(self):
        return self.role == UserRole.RIDER

    @property
    def is_admin_user(self):
        return self.role == UserRole.ADMIN
