"use client";
import { useEffect, useRef, useCallback, useState } from "react";

export type WsMessage = {
  type: string;
  data?: Record<string, unknown>;
  channel?: string;
};

type Options = {
  onMessage?: (msg: WsMessage) => void;
  reconnectDelayMs?: number;
  enabled?: boolean;
};

export function useWebSocket(channel: string, options: Options = {}) {
  const { onMessage, reconnectDelayMs = 3000, enabled = true } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;
    const wsBase = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
    const url = `${wsBase}/ws/eraya/${channel}/`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WsMessage;
        onMessage?.(msg);
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (enabled) {
        timerRef.current = setTimeout(connect, reconnectDelayMs);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [channel, enabled, onMessage, reconnectDelayMs]);

  useEffect(() => {
    connect();
    return () => {
      timerRef.current && clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((msg: WsMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { connected, send };
}
