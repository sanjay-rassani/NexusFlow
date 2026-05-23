from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "role", "is_active", "is_online", "created_at"]
    list_filter = ["role", "is_active", "is_email_verified"]
    search_fields = ["email", "first_name", "last_name", "username"]
    ordering = ["-created_at"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "NexusFlow Profile",
            {
                "fields": (
                    "role",
                    "phone_number",
                    "profile_picture",
                    "is_email_verified",
                    "is_online",
                    "last_seen",
                )
            },
        ),
    )
