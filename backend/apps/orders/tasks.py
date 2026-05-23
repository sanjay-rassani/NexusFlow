"""
Celery tasks for the orders app.

Periodic tasks (scheduled via django-celery-beat):
  auto_cancel_expired_orders — cancels CREATED orders with no vendor action
                               after a configurable timeout (default: 30 min).

One-off tasks:
  (dispatched inline from services, not scheduled)
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Orders in CREATED state older than this are auto-cancelled.
# Configurable via settings.ORDER_EXPIRY_MINUTES (default: 30).
_DEFAULT_EXPIRY_MINUTES = 30


@shared_task(name="orders.auto_cancel_expired_orders")
def auto_cancel_expired_orders() -> dict:
    """
    Periodic task (Celery beat) — scans for orders stuck in CREATED state
    for longer than ORDER_EXPIRY_MINUTES and auto-cancels them.

    Rationale: If a vendor never accepts or rejects an order within the window,
    the customer should not be left waiting indefinitely. Auto-cancellation
    restores stock and notifies the customer.

    Returns a summary dict for logging/monitoring.
    """
    from django.conf import settings

    from apps.orders.models import Order, OrderStatus
    from apps.orders.services import OrderService

    expiry_minutes = getattr(settings, "ORDER_EXPIRY_MINUTES", _DEFAULT_EXPIRY_MINUTES)
    cutoff = timezone.now() - timedelta(minutes=expiry_minutes)

    expired_orders = Order.objects.filter(
        status=OrderStatus.CREATED,
        created_at__lt=cutoff,
    ).select_related("customer", "vendor__owner")

    cancelled_ids = []
    failed_ids = []

    for order in expired_orders:
        try:
            with transaction.atomic():
                # Use a synthetic "system" user representation for the audit trail.
                # cancel_order expects the requesting user; we pass the customer
                # (who placed the order) since this cancellation acts on their behalf.
                OrderService.cancel_order(order=order, user=order.customer)
                cancelled_ids.append(str(order.id))
                logger.info(
                    "Auto-cancelled expired order %s (customer=%s, created_at=%s)",
                    order.id,
                    order.customer.email,
                    order.created_at,
                )
        except Exception as exc:
            failed_ids.append(str(order.id))
            logger.error("Failed to auto-cancel order %s: %s", order.id, exc)

    summary = {
        "checked": len(cancelled_ids) + len(failed_ids),
        "cancelled": len(cancelled_ids),
        "failed": len(failed_ids),
        "cancelled_ids": cancelled_ids,
        "failed_ids": failed_ids,
    }
    logger.info("auto_cancel_expired_orders: %s", summary)
    return summary
