"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";
import { buildWsUrl } from "@/lib/ws";
import { useChatStore } from "@/stores/chatStore";

export type WsStatus = "connecting" | "open" | "closed";

/**
 * Maintains a single authenticated WebSocket to the backend, auto-reconnects
 * with exponential backoff, pings for keep-alive, and feeds every inbound
 * server event into the Zustand chat store (live dashboard updates).
 */
export function useWebSocket(enabled: boolean): WsStatus {
  const [status, setStatus] = useState<WsStatus>("closed");

  useEffect(() => {
    if (!enabled) return;
    const token = getToken();
    if (!token) return;

    let ws: WebSocket | null = null;
    let retries = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      setStatus("connecting");

      ws = new WebSocket(`${buildWsUrl()}?token=${encodeURIComponent(token)}`);

      ws.onopen = () => {
        retries = 0;
        setStatus("open");
      };

      ws.onmessage = (evt) => {
        try {
          useChatStore.getState().applyEvent(JSON.parse(evt.data));
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onclose = () => {
        if (disposed) return;
        setStatus("closed");
        const delay = Math.min(5000, 500 * 2 ** retries);
        retries += 1;
        reconnectTimer = setTimeout(connect, delay);
      };

      ws.onerror = () => ws?.close();
    };

    connect();

    const ping = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 25_000);

    return () => {
      disposed = true;
      clearInterval(ping);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [enabled]);

  return status;
}