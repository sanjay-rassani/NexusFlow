import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { ShoppingBag } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchMyOrders, type Order } from "../../api/orders";
import { OrderStatusBadge } from "./OrderStatusBadge";

function OrderRow({ order }: { order: Order }) {
  const isActive = !["DELIVERED", "CANCELLED"].includes(order.status);

  return (
    <Link
      to={`/orders/${order.id}`}
      className="flex items-center justify-between gap-4 p-4 bg-white rounded-xl border border-gray-100 hover:border-indigo-100 hover:shadow-sm transition-all group"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-gray-900 group-hover:text-indigo-700 transition-colors">
            {order.vendor.name}
          </span>
          <OrderStatusBadge status={order.status} pulse={isActive} />
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {order.items.length} item{order.items.length !== 1 ? "s" : ""} ·{" "}
          {formatDistanceToNow(new Date(order.created_at), { addSuffix: true })}
        </p>
      </div>

      <div className="text-right flex-shrink-0">
        <span className="font-semibold text-gray-900">${order.total}</span>
      </div>
    </Link>
  );
}

export default function OrderListPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["my-orders"],
    queryFn: () => fetchMyOrders(),
    refetchInterval: 30_000,   // Poll every 30s as fallback if WS is down
    staleTime: 10_000,
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Orders</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track your orders in real time
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-16 text-gray-500">
          <p>Failed to load orders.</p>
        </div>
      ) : !data?.results.length ? (
        <div className="text-center py-16 text-gray-400">
          <ShoppingBag size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No orders yet</p>
          <Link
            to="/vendors"
            className="mt-3 inline-block text-sm text-indigo-600 hover:underline"
          >
            Browse restaurants →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {data.results.map((o) => (
            <OrderRow key={o.id} order={o} />
          ))}
        </div>
      )}
    </div>
  );
}
