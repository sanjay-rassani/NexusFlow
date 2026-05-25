import { api } from "./axios";
import type { PaginatedResponse } from "./vendors";

export type OrderStatus =
  | "CREATED"
  | "ACCEPTED"
  | "PREPARING"
  | "READY_FOR_PICKUP"
  | "PICKED_UP"
  | "ON_THE_WAY"
  | "DELIVERED"
  | "CANCELLED";

export interface OrderItem {
  id: string;
  product: { id: string; name: string; price: string };
  quantity: number;
  unit_price: string;
}

export interface Order {
  id: string;
  vendor: { id: string; name: string };
  status: OrderStatus;
  items: OrderItem[];
  subtotal: string;
  delivery_fee: string;
  total: string;
  delivery_address: string;
  created_at: string;
  updated_at: string;
}

export interface CreateOrderPayload {
  vendor: string;
  delivery_address: string;
  special_instructions?: string;
  items: Array<{ product: string; quantity: number }>;
}

export async function fetchMyOrders(params?: Record<string, string>) {
  const { data } = await api.get<PaginatedResponse<Order>>("/orders/customer/", {
    params,
  });
  return data;
}

export async function fetchOrder(id: string) {
  const { data } = await api.get<Order>(`/orders/customer/${id}/`);
  return data;
}

export async function createOrder(payload: CreateOrderPayload) {
  const { data } = await api.post<Order>("/orders/customer/", payload);
  return data;
}

export async function cancelOrder(id: string) {
  const { data } = await api.post<Order>(`/orders/customer/${id}/cancel/`);
  return data;
}
