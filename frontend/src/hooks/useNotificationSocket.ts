/**
 * Connects to ws/notifications/ and writes incoming events to the
 * notification store. Reconnects automatically with exponential back-off.
 */

import { useEffect, useRef } from "react";
import { useNotificationStore } from "../store/notificationStore";

const BASE_WS_URL = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
const MAX_RECONNECT_DELAY_MS = 30_000;

export function useNotificationSocket(enabled: boolean) {
  const { setUnreadCount, addPush, setWsStatus } = useNotificationStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelay = useRef(1_000);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    if (!enabled) return;

    function connect() {
      const token = localStorage.getItem("access_token");
      if (!token || !isMounted.current) return;

      setWsStatus("connecting");
      const ws = new WebSocket(`${BASE_WS_URL}/ws/notifications/?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus("open");
        reconnectDelay.current = 1_000; // Reset back-off on successful connect
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string);

          if (data.type === "UNREAD_COUNT") {
            setUnreadCount(data.count);
          } else if (data.type === "NOTIFICATION_PUSH" && data.notification) {
            addPush(data.notification);
            setUnreadCount(0); // Will be refreshed by the server's UNREAD_COUNT event
            useNotificationStore.getState().incrementUnread();
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setWsStatus("closed");
        if (!isMounted.current) return;

        // Exponential back-off reconnect
        reconnectTimer.current = setTimeout(() => {
          reconnectDelay.current = Math.min(
            reconnectDelay.current * 2,
            MAX_RECONNECT_DELAY_MS,
          );
          connect();
        }, reconnectDelay.current);
      };

      ws.onerror = () => {
        setWsStatus("error");
        ws.close();
      };
    }

    connect();

    return () => {
      isMounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [enabled, setUnreadCount, addPush, setWsStatus]);
}
