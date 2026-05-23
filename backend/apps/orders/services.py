"""
Order business logic service layer.

Critical design decisions:

1. Order creation is fully atomic — if stock deduction fails for any item,
   the entire transaction rolls back. No partial orders ever persist.

2. State machine transitions are enforced here, not in views. Views are
   purely HTTP adapters; they call services and return responses.

3. Stock is deducted on order CREATED and restored on CANCELLED.
   This means stock is "reserved" at placement time, preventing overselling.

4. The service emits a hook point for WebSocket events (Phase 5).
   Currently a no-op, but the call sites are already in place.
"""

import logging
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers as drf_serializers

from apps.vendors.services import ProductService

from .models import Order, OrderItem, OrderStatus, OrderStatusHistory, ORDER_STATUS_TRANSITIONS

logger = logging.getLogger(__name__)

# Delivery fee constants (simplified — real system would calculate from distance)
BASE_DELIVERY_FEE = Decimal("2.00")


class OrderService:

    # ──────────────────────────────────────────
    # Order creation
    # ──────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_order(customer, validated_data: dict) -> Order:
        """
        Place an order atomically:
          1. Deduct stock for all items (SELECT FOR UPDATE inside ProductService)
          2. Snapshot unit prices (prices may change later; order price is fixed)
          3. Create Order + OrderItems + initial status history entry

        Raises ValidationError if any item has insufficient stock.
        The entire transaction rolls back on any failure.
        """
        vendor = validated_data["vendor"]
        items_data = validated_data["items"]
        delivery_fee = validated_data.get("delivery_fee", BASE_DELIVERY_FEE)

        # Deduct stock for every item — rolls back all on any failure
        for item_data in items_data:
            product = item_data["product"]
            quantity = item_data["quantity"]
            success = ProductService.deduct_stock(product.pk, quantity)
            if not success:
                raise drf_serializers.ValidationError(
                    {
                        "items": (
                            f"Insufficient stock for '{product.name}'. "
                            f"Please reduce quantity and try again."
                        )
                    }
                )

        # Calculate totals using price snapshot at order time
        subtotal = Decimal("0.00")
        item_snapshots = []
        for item_data in items_data:
            product = item_data["product"]
            quantity = item_data["quantity"]
            unit_price = product.price  # snapshot — locked at placement time
            line_subtotal = unit_price * quantity
            subtotal += line_subtotal
            item_snapshots.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": line_subtotal,
                }
            )

        total = subtotal + delivery_fee

        order = Order.objects.create(
            customer=customer,
            vendor=vendor,
            delivery_address=validated_data["delivery_address"],
            special_instructions=validated_data.get("special_instructions", ""),
            delivery_fee=delivery_fee,
            subtotal=subtotal,
            total=total,
            status=OrderStatus.CREATED,
        )

        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=snap["product"],
                    quantity=snap["quantity"],
                    unit_price=snap["unit_price"],
                    subtotal=snap["subtotal"],
                )
                for snap in item_snapshots
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            from_status="",
            to_status=OrderStatus.CREATED,
            changed_by=customer,
            note="Order placed.",
        )

        logger.info(
            "Order %s created — customer=%s vendor=%s total=%s",
            order.id,
            customer.email,
            vendor.name,
            total,
        )

        # Phase 5 hook — emit WebSocket event to vendor
        OrderService._emit_event("NEW_ORDER", order)

        return order

    # ──────────────────────────────────────────
    # State machine
    # ──────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def transition_status(
        order: Order,
        new_status: str,
        changed_by,
        note: str = "",
    ) -> Order:
        """
        Validates and applies a status transition.
        Raises ValidationError if the transition is not permitted.
        """
        current = order.status
        allowed = [s.value for s in ORDER_STATUS_TRANSITIONS.get(current, [])]

        if new_status not in allowed:
            raise drf_serializers.ValidationError(
                {
                    "status": (
                        f"Cannot transition from '{current}' to '{new_status}'. "
                        f"Allowed: {allowed or ['none']}."
                    )
                }
            )

        old_status = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            note=note,
        )

        logger.info(
            "Order %s: %s → %s (by %s)",
            order.id,
            old_status,
            new_status,
            changed_by.email,
        )

        # Phase 5 hook — emit WebSocket event to customer + vendor
        OrderService._emit_event("ORDER_STATUS_UPDATED", order)

        return order

    # ──────────────────────────────────────────
    # Customer actions
    # ──────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def cancel_order(order: Order, user) -> Order:
        """
        Customer cancels their own order.
        Only valid from CREATED or ACCEPTED state.
        Restores stock for all items.
        """
        cancellable = [OrderStatus.CREATED, OrderStatus.ACCEPTED]
        if order.status not in cancellable:
            raise drf_serializers.ValidationError(
                {
                    "detail": (
                        f"Orders in '{order.status}' state cannot be cancelled. "
                        f"Only CREATED or ACCEPTED orders can be cancelled by customers."
                    )
                }
            )

        # Restore stock before transitioning (both inside same atomic block)
        for item in order.items.select_related("product"):
            ProductService.restore_stock(item.product.pk, item.quantity)

        order = OrderService.transition_status(
            order, OrderStatus.CANCELLED, user, note="Cancelled by customer."
        )
        return order

    # ──────────────────────────────────────────
    # Vendor actions
    # ──────────────────────────────────────────

    @staticmethod
    def accept_order(order: Order, vendor_user) -> Order:
        return OrderService.transition_status(
            order, OrderStatus.ACCEPTED, vendor_user, note="Order accepted by vendor."
        )

    @staticmethod
    def reject_order(order: Order, vendor_user) -> Order:
        """Vendor rejects — restore stock and cancel."""
        for item in order.items.select_related("product"):
            ProductService.restore_stock(item.product.pk, item.quantity)
        return OrderService.transition_status(
            order, OrderStatus.CANCELLED, vendor_user, note="Order rejected by vendor."
        )

    @staticmethod
    def start_preparing(order: Order, vendor_user) -> Order:
        return OrderService.transition_status(
            order, OrderStatus.PREPARING, vendor_user, note="Preparation started."
        )

    @staticmethod
    def mark_ready(order: Order, vendor_user) -> Order:
        return OrderService.transition_status(
            order, OrderStatus.READY_FOR_PICKUP, vendor_user, note="Order ready for pickup."
        )

    # ──────────────────────────────────────────
    # Rider actions
    # ──────────────────────────────────────────

    @staticmethod
    def pickup_order(order: Order, rider) -> Order:
        return OrderService.transition_status(
            order, OrderStatus.PICKED_UP, rider, note="Order picked up by rider."
        )

    @staticmethod
    def mark_on_the_way(order: Order, rider) -> Order:
        return OrderService.transition_status(
            order, OrderStatus.ON_THE_WAY, rider, note="Order on the way."
        )

    @staticmethod
    def mark_delivered(order: Order, rider) -> Order:
        return OrderService.transition_status(
            order, OrderStatus.DELIVERED, rider, note="Order delivered."
        )

    # ──────────────────────────────────────────
    # Admin actions
    # ──────────────────────────────────────────

    @staticmethod
    def assign_rider(order: Order, rider, admin) -> Order:
        """
        Assign a rider to an order.
        Rider can be assigned from ACCEPTED through READY_FOR_PICKUP.
        """
        assignable = [
            OrderStatus.ACCEPTED,
            OrderStatus.PREPARING,
            OrderStatus.READY_FOR_PICKUP,
        ]
        if order.status not in assignable:
            raise drf_serializers.ValidationError(
                {
                    "detail": (
                        f"Rider can only be assigned to orders in "
                        f"ACCEPTED, PREPARING, or READY_FOR_PICKUP state. "
                        f"Current status: {order.status}."
                    )
                }
            )

        order.rider = rider
        order.save(update_fields=["rider", "updated_at"])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=order.status,
            to_status=order.status,
            changed_by=admin,
            note=f"Rider assigned: {rider.email}",
        )

        logger.info(
            "Rider %s assigned to order %s by admin %s",
            rider.email,
            order.id,
            admin.email,
        )

        # Add rider to the order's chat room so they can communicate
        # with the customer and vendor. Room is created lazily if absent.
        try:
            from apps.chat.services import ChatService
            room = ChatService.get_or_create_room(order)
            ChatService.add_participant(room, rider)
        except Exception as exc:
            # Chat room failure must never break order assignment
            logger.warning("Failed to add rider to chat room for order %s: %s", order.id, exc)

        OrderService._emit_event("RIDER_ASSIGNED", order)

        return order

    # ──────────────────────────────────────────
    # Queryset helpers (used by views)
    # ──────────────────────────────────────────

    @staticmethod
    def get_order_queryset_base():
        """Base queryset with all necessary joins pre-loaded."""
        return (
            Order.objects
            .select_related("customer", "vendor", "rider")
            .prefetch_related("items__product", "status_history__changed_by")
        )

    @staticmethod
    def get_order_for_customer(order_id, customer):
        """Returns order only if it belongs to this customer."""
        try:
            return OrderService.get_order_queryset_base().get(
                pk=order_id, customer=customer
            )
        except Order.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Order not found.")

    @staticmethod
    def get_order_for_vendor(order_id, vendor):
        """Returns order only if it belongs to this vendor."""
        try:
            return OrderService.get_order_queryset_base().get(
                pk=order_id, vendor=vendor
            )
        except Order.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Order not found.")

    @staticmethod
    def get_order_for_rider(order_id, rider):
        """Returns order only if this rider is assigned."""
        try:
            return OrderService.get_order_queryset_base().get(
                pk=order_id, rider=rider
            )
        except Order.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Order not found.")

    # ──────────────────────────────────────────
    # WebSocket event emission
    # ──────────────────────────────────────────

    @staticmethod
    def _emit_event(event_type: str, order: Order) -> None:
        """
        Broadcasts real-time events to all parties subscribed to an order
        AND persists DB notifications so users can retrieve history later.

        Event routing (WebSocket channels):
          NEW_ORDER            → vendor personal notification channel + order channel
          ORDER_STATUS_UPDATED → order channel + customer notification channel
          RIDER_ASSIGNED       → order channel + customer + rider notification channels

        DB notifications persisted:
          NEW_ORDER            → vendor
          ORDER_STATUS_UPDATED → customer (+ rider if assigned)
          RIDER_ASSIGNED       → customer + rider

        All sends are deferred via transaction.on_commit so phantom events
        are never emitted if the DB transaction rolls back.
        Notification creation failures are caught and logged — they must
        never break the primary order operation.
        """
        from apps.notifications.models import NotificationType
        from apps.notifications.services import NotificationService
        from core.channel_utils import broadcast_to_order, broadcast_to_user

        order_payload = {
            "type": "ORDER_STATUS_UPDATED",
            "order_id": str(order.id),
            "status": order.status,
            "updated_at": order.updated_at.isoformat(),
        }

        if event_type == "NEW_ORDER":
            # ── Persist notification ─────────────────────────────────────────
            try:
                NotificationService.create(
                    recipient=order.vendor.owner,
                    notification_type=NotificationType.NEW_ORDER,
                    title="New Order Received",
                    message=(
                        f"New order from {order.customer.full_name or order.customer.email} "
                        f"— total {order.total}"
                    ),
                    data={"order_id": str(order.id), "status": order.status},
                )
            except Exception as exc:
                logger.error("Failed to persist NEW_ORDER notification for order %s: %s", order.id, exc)

            # ── Real-time WS events ──────────────────────────────────────────
            broadcast_to_user(
                order.vendor.owner_id,
                {
                    "type": "notification.push",
                    "data": {
                        "type": "NEW_ORDER",
                        "order_id": str(order.id),
                        "customer_name": order.customer.full_name or order.customer.email,
                        "total": str(order.total),
                        "vendor_name": order.vendor.name,
                    },
                },
            )
            broadcast_to_order(order.id, {
                "type": "order.status.updated",
                "data": order_payload,
            })

        elif event_type == "ORDER_STATUS_UPDATED":
            # ── Persist notification ─────────────────────────────────────────
            try:
                NotificationService.create(
                    recipient=order.customer,
                    notification_type=NotificationType.ORDER_STATUS,
                    title=f"Order {order.status.replace('_', ' ').title()}",
                    message=f"Your order status has been updated to {order.status}.",
                    data={"order_id": str(order.id), "status": order.status},
                )
                if order.rider:
                    NotificationService.create(
                        recipient=order.rider,
                        notification_type=NotificationType.ORDER_STATUS,
                        title=f"Order {order.status.replace('_', ' ').title()}",
                        message=f"Order {order.id} status: {order.status}.",
                        data={"order_id": str(order.id), "status": order.status},
                    )
            except Exception as exc:
                logger.error("Failed to persist ORDER_STATUS notification for order %s: %s", order.id, exc)

            # ── Real-time WS events ──────────────────────────────────────────
            broadcast_to_order(order.id, {
                "type": "order.status.updated",
                "data": order_payload,
            })
            broadcast_to_user(
                order.customer_id,
                {
                    "type": "notification.push",
                    "data": {
                        "type": "ORDER_STATUS_UPDATED",
                        "order_id": str(order.id),
                        "status": order.status,
                    },
                },
            )

        elif event_type == "RIDER_ASSIGNED":
            rider_data = {
                "type": "RIDER_ASSIGNED",
                "order_id": str(order.id),
                "rider_id": str(order.rider_id) if order.rider_id else None,
                "rider_email": order.rider.email if order.rider else None,
            }

            # ── Persist notifications ────────────────────────────────────────
            try:
                NotificationService.create(
                    recipient=order.customer,
                    notification_type=NotificationType.RIDER_ASSIGNED,
                    title="Rider Assigned to Your Order",
                    message=(
                        f"Rider {order.rider.full_name or order.rider.email} "
                        f"has been assigned to your order."
                    ),
                    data=rider_data,
                )
                if order.rider:
                    NotificationService.create(
                        recipient=order.rider,
                        notification_type=NotificationType.RIDER_ASSIGNED,
                        title="New Delivery Assignment",
                        message=f"You have been assigned to order {order.id}.",
                        data=rider_data,
                    )
            except Exception as exc:
                logger.error("Failed to persist RIDER_ASSIGNED notification for order %s: %s", order.id, exc)

            # ── Real-time WS events ──────────────────────────────────────────
            broadcast_to_order(order.id, {
                "type": "rider.assigned",
                "data": rider_data,
            })
            broadcast_to_user(
                order.customer_id,
                {
                    "type": "notification.push",
                    "data": rider_data,
                },
            )

        else:
            # Generic fallback — broadcast to order channel only (no DB notification)
            broadcast_to_order(order.id, {
                "type": "order.status.updated",
                "data": order_payload,
            })

        logger.debug("Event [%s] emitted for order %s.", event_type, order.id)
