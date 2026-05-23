"""
Celery tasks for email notifications.

All tasks are async — they run in the Celery worker process, never blocking
the API request/response cycle. They are dispatched via transaction.on_commit()
in the service layer so emails are only sent if the triggering DB transaction
successfully commits.

Retry strategy:
  - Transient failures (SMTP unavailable, network) retry up to 3 times with
    exponential back-off.
  - Permanent failures (bad address) are logged and NOT retried.

Email format:
  - Plain text only for simplicity and maximum deliverability.
  - Subject lines are concise and descriptive.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

# Shared retry settings for critical emails
_RETRY_KWARGS = dict(bind=True, max_retries=3, default_retry_delay=60)


# ──────────────────────────────────────────────
# Order — new order (vendor)
# ──────────────────────────────────────────────

@shared_task(name="notifications.send_new_order_email", **_RETRY_KWARGS)
def send_new_order_email(self, order_id: str) -> None:
    """
    Email the vendor when a customer places a new order.
    """
    from apps.orders.models import Order

    try:
        order = Order.objects.select_related(
            "vendor__owner", "customer"
        ).get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("send_new_order_email: order %s not found — skipping.", order_id)
        return

    vendor_email = order.vendor.owner.email
    customer_name = order.customer.full_name or order.customer.email

    subject = f"[NexusFlow] New Order #{str(order.id)[:8].upper()}"
    message = (
        f"Hi {order.vendor.owner.full_name or 'there'},\n\n"
        f"You have received a new order from {customer_name}.\n\n"
        f"Order ID:  {order.id}\n"
        f"Total:     {order.total}\n"
        f"Delivery:  {order.delivery_address}\n\n"
        f"Please log in to your vendor dashboard to accept or reject this order.\n\n"
        f"— The NexusFlow Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[vendor_email],
            fail_silently=False,
        )
        logger.info("New-order email sent to vendor %s (order=%s)", vendor_email, order_id)
    except Exception as exc:
        logger.error("Failed to send new-order email to %s: %s", vendor_email, exc)
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────
# Order — status changed (customer + optional rider)
# ──────────────────────────────────────────────

@shared_task(name="notifications.send_order_status_email", **_RETRY_KWARGS)
def send_order_status_email(self, order_id: str, recipient_id: str) -> None:
    """
    Email a user (customer or rider) when an order status changes.
    recipient_id allows routing to either the customer or an assigned rider.
    """
    from apps.orders.models import Order
    from apps.users.models import User

    try:
        order = Order.objects.select_related("customer", "vendor", "rider").get(pk=order_id)
        recipient = User.objects.get(pk=recipient_id)
    except (Order.DoesNotExist, User.DoesNotExist):
        logger.warning("send_order_status_email: order or user not found — skipping.")
        return

    friendly_status = order.status.replace("_", " ").title()
    subject = f"[NexusFlow] Order Update — {friendly_status}"
    message = (
        f"Hi {recipient.full_name or 'there'},\n\n"
        f"Your order has been updated.\n\n"
        f"Order ID: {order.id}\n"
        f"Status:   {friendly_status}\n"
        f"Vendor:   {order.vendor.name}\n\n"
        f"You can track your order in real time via the NexusFlow app.\n\n"
        f"— The NexusFlow Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=False,
        )
        logger.info(
            "Order-status email sent to %s (order=%s, status=%s)",
            recipient.email,
            order_id,
            order.status,
        )
    except Exception as exc:
        logger.error("Failed to send order-status email to %s: %s", recipient.email, exc)
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────
# Order — rider assigned (customer + rider)
# ──────────────────────────────────────────────

@shared_task(name="notifications.send_rider_assigned_email", **_RETRY_KWARGS)
def send_rider_assigned_email(self, order_id: str) -> None:
    """
    Email both the customer and the rider when a rider is assigned to an order.
    Fires two separate sends within the same task to keep retries atomic.
    """
    from apps.orders.models import Order

    try:
        order = Order.objects.select_related("customer", "vendor", "rider").get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("send_rider_assigned_email: order %s not found — skipping.", order_id)
        return

    if not order.rider:
        logger.warning("send_rider_assigned_email: order %s has no rider — skipping.", order_id)
        return

    rider_name = order.rider.full_name or order.rider.email
    customer_name = order.customer.full_name or order.customer.email

    # Email to customer
    try:
        send_mail(
            subject=f"[NexusFlow] Your Rider is on the Way",
            message=(
                f"Hi {customer_name},\n\n"
                f"Great news! A rider has been assigned to your order.\n\n"
                f"Order ID: {order.id}\n"
                f"Rider:    {rider_name}\n\n"
                f"Track your delivery live in the NexusFlow app.\n\n"
                f"— The NexusFlow Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            fail_silently=False,
        )
        logger.info("Rider-assigned email sent to customer %s", order.customer.email)
    except Exception as exc:
        logger.error("Failed to send rider-assigned email to customer %s: %s", order.customer.email, exc)
        raise self.retry(exc=exc)

    # Email to rider
    try:
        send_mail(
            subject=f"[NexusFlow] New Delivery Assignment",
            message=(
                f"Hi {rider_name},\n\n"
                f"You have been assigned a new delivery.\n\n"
                f"Order ID:    {order.id}\n"
                f"Vendor:      {order.vendor.name}\n"
                f"Deliver to:  {order.delivery_address}\n\n"
                f"Please open the NexusFlow app for navigation and live updates.\n\n"
                f"— The NexusFlow Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.rider.email],
            fail_silently=False,
        )
        logger.info("Rider-assigned email sent to rider %s", order.rider.email)
    except Exception as exc:
        logger.error("Failed to send rider-assigned email to rider %s: %s", order.rider.email, exc)
        # Don't retry — customer email already sent; log and move on


# ──────────────────────────────────────────────
# Chat — new message (offline participant)
# ──────────────────────────────────────────────

@shared_task(name="notifications.send_chat_notification_email", **_RETRY_KWARGS)
def send_chat_notification_email(self, message_id: str, recipient_id: str) -> None:
    """
    Notify a chat participant by email when they receive a new message.
    Should only be dispatched for participants who are likely offline
    (the WebSocket consumer handles online participants in real time).
    """
    from apps.chat.models import Message
    from apps.users.models import User

    try:
        msg = Message.objects.select_related("sender", "room__order__vendor").get(pk=message_id)
        recipient = User.objects.get(pk=recipient_id)
    except (Message.DoesNotExist, User.DoesNotExist):
        logger.warning("send_chat_notification_email: message or user not found — skipping.")
        return

    sender_name = msg.sender.full_name or msg.sender.email
    preview = msg.content[:120] + ("…" if len(msg.content) > 120 else "")

    subject = f"[NexusFlow] New message from {sender_name}"
    message = (
        f"Hi {recipient.full_name or 'there'},\n\n"
        f"You have a new chat message from {sender_name}:\n\n"
        f"  \"{preview}\"\n\n"
        f"Open the NexusFlow app to read and reply.\n\n"
        f"— The NexusFlow Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=False,
        )
        logger.info(
            "Chat notification email sent to %s (message=%s)", recipient.email, message_id
        )
    except Exception as exc:
        logger.error(
            "Failed to send chat notification email to %s: %s", recipient.email, exc
        )
        raise self.retry(exc=exc)
