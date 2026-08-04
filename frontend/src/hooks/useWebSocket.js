"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "@/lib/api";

export function useWebSocket({ path, onMessage, enabled = true }) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [reconnectCount, setReconnectCount] = useState(0);
  const wsRef = useRef(null);
  const retryRef = useRef(0);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const send = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === "string" ? data : JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    retryRef.current = 0;
    setReconnectCount((c) => c + 1);
  }, [disconnect]);

  useEffect(() => {
    if (!enabled) return undefined;

    let cancelled = false;
    let timer = null;
    let reconnectScheduled = false;

    function scheduleReconnect() {
      if (cancelled || reconnectScheduled) return;
      reconnectScheduled = true;
      const delay = Math.min(15_000, 500 * 2 ** retryRef.current);
      timer = setTimeout(() => {
        reconnectScheduled = false;
        retryRef.current = Math.min(retryRef.current + 1, 8);
        connect();
      }, delay);
    }

    function connect() {
      if (cancelled) return;
      try {
        const ws = new WebSocket(api.wsUrl(path));
        wsRef.current = ws;

        ws.onopen = () => {
          if (cancelled) {
            ws.close();
            return;
          }
          setConnected(true);
          retryRef.current = 0;
        };

        ws.onmessage = (event) => {
          if (cancelled) return;
          try {
            const data = JSON.parse(event.data);
            setLastMessage(data);
            onMessageRef.current?.(data);
          } catch {
            // ignore non-JSON frames
          }
        };

        ws.onerror = () => {};

        ws.onclose = () => {
          setConnected(false);
          wsRef.current = null;
          scheduleReconnect();
        };
      } catch {
        scheduleReconnect();
      }
    }

    connect();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      const ws = wsRef.current;
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
      wsRef.current = null;
    };
  }, [path, enabled, reconnectCount]);

  return { connected, lastMessage, send, disconnect, reconnect };
}

export function useRealtimeSubscription(path, { enabled = true, onEvent } = {}) {
  const [events, setEvents] = useState([]);
  const [isLive, setIsLive] = useState(false);
  const maxEvents = 100;

  const handleMessage = useCallback(
    (data) => {
      setIsLive(true);
      setEvents((prev) => {
        const next = [...prev, { ...data, _receivedAt: Date.now() }];
        return next.slice(-maxEvents);
      });
      onEvent?.(data);
    },
    [onEvent],
  );

  const { connected } = useWebSocket({ path, onMessage: handleMessage, enabled });

  const clearEvents = useCallback(() => setEvents([]), []);

  const latestByType = useCallback(
    (type) => {
      for (let i = events.length - 1; i >= 0; i--) {
        if (events[i].type === type) return events[i];
      }
      return null;
    },
    [events],
  );

  const filterByType = useCallback(
    (type) => events.filter((e) => e.type === type),
    [events],
  );

  return {
    connected,
    isLive,
    events,
    clearEvents,
    latestByType,
    filterByType,
  };
}

export default useWebSocket;
