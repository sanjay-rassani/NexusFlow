/**
 * Live order detail page.
 *
 * Connects to ws/orders/<order_id>/ for real-time status updates.
 * When an ORDER_STATUS_UPDATED event arrives, the status badge updates
 * immediately without a full page refresh.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { ArrowLeft, MapPin } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { cancelOrder, fetchOrder, type OrderStatus } from "../../api/orders";
import { OrderStatusBadge } from "./OrderStatusBadge";

const BASE_WS_URL = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

function useOrderSocket(orderId: string, onStatusUpdate: (status: OrderStatus) => void) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token || !orderId) return;

    const ws = new WebSocket(
      `${BASE_WS_URL}/ws/orders/${orderId}/?token=${token}`,
    );
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === "ORDER_STATUS_UPDATED" && data.status) {
          onStatusUpdate(data.status as OrderStatus);
        }
      } catch {
        /* ignore */
      }
    };

    return () => ws.close();
  }, [orderId, onStatusUpdate]);
}

const ACTIVE_STATUSES = new Set<OrderStatus>([
  "CREATED",
  "ACCEPTED",
  "PREPARING",
  "READY_FOR_PICKUP",
  "PICKED_UP",
  "ON_THE_WAY",
]);

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [liveStatus, setLiveStatus] = useState<OrderStatus | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const { data: order, isLoading } = useQuery({
    queryKey: ["order", id],
    queryFn: () => fetchOrder(id!),
    enabled: !!id,
    staleTime: 30_000,
  });

  // WebSocket live status updates
  useOrderSocket(id ?? "", (status) => {
    setLiveStatus(status);
    // Also invalidate the query cache so a re-fetch shows the updated status
    queryClient.invalidateQueries({ queryKey: ["order", id] });
    queryClient.invalidateQueries({ queryKey: ["my-orders"] });
  });

  const displayStatus = liveStatus ?? order?.status;
  const isActive = displayStatus ? ACTIVE_STATUSES.has(displayStatus) : false;

  async function handleCancel() {
    if (!id || !window.confirm("Cancel this order?")) return;
    setCancelling(true);
    try {
      await cancelOrder(id);
      setLiveStatus("CANCELLED");
      queryClient.invalidateQueries({ queryKey: ["order", id] });
      queryClient.invalidateQueries({ queryKey: ["my-orders"] });
    } finally {
      setCancelling(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-40 rounded bg-gray-100 animate-pulse" />
        <div className="h-48 rounded-2xl bg-gray-100 animate-pulse" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p>Order not found.</p>
        <Link to="/orders" className="text-indigo-600 text-sm mt-2 inline-block hover:underline">
          ← Back to orders
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Link
        to="/orders"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-5 transition-colors"
      >
        <ArrowLeft size={15} />
        My orders
      </Link>

      {/* Status card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-lg font-bold text-gray-900">
              Order from {order.vendor.name}
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Placed{" "}
              {formatDistanceToNow(new Date(order.created_at), {
                addSuffix: true,
              })}
            </p>
          </div>

          {displayStatus && (
            <OrderStatusBadge status={displayStatus} pulse={isActive} />
          )}
        </div>

        {/* Live indicator */}
        {isActive && (
          <div className="mt-4 flex items-center gap-2 text-xs text-indigo-500">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            Tracking live via WebSocket
          </div>
        )}

        {/* Delivery address */}
        <div className="flex items-start gap-2 mt-4 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
          <MapPin size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
          {order.delivery_address}
        </div>
      </div>

      {/* Items */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-4">
        <h2 className="font-semibold text-gray-900 mb-3">Items</h2>
        <div className="space-y-2">
          {order.items.map((item) => (
            <div key={item.id} className="flex items-center justify-between text-sm">
              <span className="text-gray-700">
                {item.quantity}× {item.product.name}
              </span>
              <span className="text-gray-900 font-medium">
                ${(parseFloat(item.unit_price) * item.quantity).toFixed(2)}
              </span>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-100 mt-4 pt-4 space-y-1">
          <div className="flex justify-between text-sm text-gray-500">
            <span>Subtotal</span>
            <span>${order.subtotal}</span>
          </div>
          <div className="flex justify-between text-sm text-gray-500">
            <span>Delivery</span>
            <span>${order.delivery_fee}</span>
          </div>
          <div className="flex justify-between font-semibold text-gray-900 text-sm pt-1 border-t border-gray-100">
            <span>Total</span>
            <span>${order.total}</span>
          </div>
        </div>
      </div>

      {/* Cancel button — only for CREATED orders */}
      {displayStatus === "CREATED" && (
        <button
          onClick={handleCancel}
          disabled={cancelling}
          className="w-full rounded-xl border border-red-200 text-red-600 text-sm font-medium py-3 hover:bg-red-50 disabled:opacity-50 transition-colors"
        >
          {cancelling ? "Cancelling…" : "Cancel Order"}
        </button>
      )}
    </div>
  );
}
