import type { OrderStatus } from "../../api/orders";

const STATUS_CONFIG: Record<
  OrderStatus,
  { label: string; color: string; dot: string }
> = {
  CREATED:          { label: "Placed",           color: "bg-blue-50 text-blue-700",   dot: "bg-blue-400" },
  ACCEPTED:         { label: "Accepted",          color: "bg-indigo-50 text-indigo-700", dot: "bg-indigo-400" },
  PREPARING:        { label: "Preparing",         color: "bg-yellow-50 text-yellow-700", dot: "bg-yellow-400" },
  READY_FOR_PICKUP: { label: "Ready",             color: "bg-orange-50 text-orange-700", dot: "bg-orange-400" },
  PICKED_UP:        { label: "Picked Up",         color: "bg-purple-50 text-purple-700", dot: "bg-purple-400" },
  ON_THE_WAY:       { label: "On the Way",        color: "bg-cyan-50 text-cyan-700",   dot: "bg-cyan-400" },
  DELIVERED:        { label: "Delivered",         color: "bg-green-50 text-green-700", dot: "bg-green-500" },
  CANCELLED:        { label: "Cancelled",         color: "bg-red-50 text-red-700",     dot: "bg-red-400" },
};

interface Props {
  status: OrderStatus;
  pulse?: boolean;
}

export function OrderStatusBadge({ status, pulse = false }: Props) {
  const cfg = STATUS_CONFIG[status] ?? {
    label: status,
    color: "bg-gray-50 text-gray-600",
    dot: "bg-gray-400",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.color}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${pulse ? "animate-pulse" : ""}`}
      />
      {cfg.label}
    </span>
  );
}
