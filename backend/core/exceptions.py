"""
Custom exception handler — normalizes all error responses to a consistent shape.

All errors return:
{
    "error": true,
    "code": "VALIDATION_ERROR",
    "message": "...",
    "details": {...}   // optional field-level errors
}
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "error": True,
            "code": _get_error_code(exc),
            "message": _get_error_message(response.data),
            "details": _get_error_details(response.data),
        }
        response.data = error_data
        return response

    # Unhandled exceptions — return 500 and log
    logger.exception("Unhandled exception in view: %s", exc)
    return Response(
        {
            "error": True,
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "details": None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_error_code(exc):
    from rest_framework.exceptions import (
        AuthenticationFailed,
        NotAuthenticated,
        PermissionDenied as DRFPermissionDenied,
        ValidationError,
    )

    mapping = {
        ValidationError: "VALIDATION_ERROR",
        NotAuthenticated: "NOT_AUTHENTICATED",
        AuthenticationFailed: "AUTHENTICATION_FAILED",
        DRFPermissionDenied: "PERMISSION_DENIED",
        PermissionDenied: "PERMISSION_DENIED",
        Http404: "NOT_FOUND",
    }
    return mapping.get(type(exc), "API_ERROR")


def _get_error_message(data):
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        return "Validation failed. Check the details field."
    if isinstance(data, list):
        return str(data[0]) if data else "An error occurred."
    return str(data)


def _get_error_details(data):
    if isinstance(data, dict) and "detail" not in data:
        return data
    return None


class NexusFlowException(Exception):
    """Base exception for NexusFlow domain errors."""

    default_message = "An error occurred."
    default_code = "NEXUSFLOW_ERROR"

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)


class InvalidOrderTransitionError(NexusFlowException):
    default_message = "Invalid order status transition."
    default_code = "INVALID_ORDER_TRANSITION"


class OrderNotFoundError(NexusFlowException):
    default_message = "Order not found."
    default_code = "ORDER_NOT_FOUND"


class UnauthorizedActionError(NexusFlowException):
    default_message = "You are not authorized to perform this action."
    default_code = "UNAUTHORIZED_ACTION"
