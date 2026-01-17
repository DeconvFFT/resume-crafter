"use client";

import { useEffect, useRef, useCallback, useState } from "react";

export type SSEEvent = {
  type: string;
  data: unknown;
  timestamp: string;
};

export type SSEConnectionState = "connecting" | "connected" | "disconnected" | "error";

export type UseSSEOptions = {
  url: string;
  enabled?: boolean;
  onMessage?: (event: SSEEvent) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
};

export function useSSE({
  url,
  enabled = true,
  onMessage,
  onError,
  onOpen,
  onClose,
  reconnectAttempts = 3,
  reconnectInterval = 2000,
}: UseSSEOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [connectionState, setConnectionState] = useState<SSEConnectionState>("disconnected");
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setConnectionState("disconnected");
    onClose?.();
  }, [onClose]);

  const connect = useCallback(() => {
    if (!enabled || !url) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setConnectionState("connecting");

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnectionState("connected");
      reconnectCountRef.current = 0;
      onOpen?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        // Backend sends event_type, normalize to type for frontend
        const normalized: SSEEvent = {
          type: parsed.event_type || parsed.type || "unknown",
          data: parsed.data || {},
          timestamp: parsed.timestamp || new Date().toISOString(),
        };
        setLastEvent(normalized);
        onMessage?.(normalized);
      } catch {
        // Handle non-JSON messages
        const fallback: SSEEvent = {
          type: "raw",
          data: event.data,
          timestamp: new Date().toISOString(),
        };
        setLastEvent(fallback);
        onMessage?.(fallback);
      }
    };

    eventSource.onerror = (error) => {
      setConnectionState("error");
      onError?.(error);

      // Attempt reconnection
      if (reconnectCountRef.current < reconnectAttempts) {
        reconnectCountRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      } else {
        disconnect();
      }
    };
  }, [url, enabled, onMessage, onError, onOpen, reconnectAttempts, reconnectInterval, disconnect]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    connectionState,
    lastEvent,
    reconnect: connect,
    disconnect,
  };
}
