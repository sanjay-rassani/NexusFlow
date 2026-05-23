"""
Custom DRF permission classes for role-based access control.
"""

from rest_framework.permissions import BasePermission

from apps.users.models import UserRole


class IsCustomer(BasePermission):
    """Allow access only to users with CUSTOMER role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.CUSTOMER
        )


class IsVendor(BasePermission):
    """Allow access only to users with VENDOR role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.VENDOR
        )


class IsRider(BasePermission):
    """Allow access only to users with RIDER role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.RIDER
        )


class IsAdminUser(BasePermission):
    """Allow access only to users with ADMIN role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.ADMIN
        )


class IsVendorOrAdmin(BasePermission):
    """Allow vendors and admins."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.VENDOR, UserRole.ADMIN)
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: allow access only if the requesting user
    is the owner of the object, or is an admin.
    Objects must have an `owner`, `user`, or `customer` attribute.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.ADMIN:
            return True
        for attr in ("owner", "user", "customer", "sender", "recipient"):
            if hasattr(obj, attr) and getattr(obj, attr) == request.user:
                return True
        return False
