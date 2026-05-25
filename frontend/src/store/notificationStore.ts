/**
 * Zustand notification store — tracks unread count and recent push events.
 *
 * The NotificationBell component subscribes here. The WebSocket hook writes here
 * whenever a NOTIFICATION_PUSH event arrives from ws/notifications/.
 */

import { create } from "zustand";
import type { Notification } from "../api/notifications";

interface NotificationState {
  unreadCount: number;
  recentPushes: Notification[];          // last 20 live pushes (not full history)
  wsStatus: "connecting" | "open" | "closed" | "error";

  setUnreadCount: (count: number) => void;
  incrementUnread: () => void;
  decrementUnread: (by?: number) => void;
  addPush: (n: Notification) => void;
  setWsStatus: (status: NotificationState["wsStatus"]) => void;
  reset: () => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  unreadCount: 0,
  recentPushes: [],
  wsStatus: "closed",

  setUnreadCount: (count) => set({ unreadCount: Math.max(0, count) }),
  incrementUnread: () =>
    set((s) => ({ unreadCount: s.unreadCount + 1 })),
  decrementUnread: (by = 1) =>
    set((s) => ({ unreadCount: Math.max(0, s.unreadCount - by) })),

  addPush: (n) =>
    set((s) => ({
      recentPushes: [n, ...s.recentPushes].slice(0, 20),
    })),

  setWsStatus: (wsStatus) => set({ wsStatus }),

  reset: () => set({ unreadCount: 0, recentPushes: [], wsStatus: "closed" }),
}));
