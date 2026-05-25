import { api } from "./axios";
import type { PaginatedResponse } from "./vendors";

export interface Notification {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  data: Record<string, unknown>;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export async function fetchNotifications(params?: Record<string, string>) {
  const { data } = await api.get<PaginatedResponse<Notification>>(
    "/notifications/",
    { params },
  );
  return data;
}

export async function fetchUnreadCount() {
  const { data } = await api.get<{ count: number }>(
    "/notifications/unread-count/",
  );
  return data.count;
}

export async function markNotificationRead(id: string) {
  await api.post(`/notifications/${id}/read/`);
}

export async function markAllNotificationsRead() {
  const { data } = await api.post<{ marked_count: number }>(
    "/notifications/read-all/",
  );
  return data.marked_count;
}
