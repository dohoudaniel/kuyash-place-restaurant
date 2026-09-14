"use client";

import { useEffect, useState } from "react";
import { FINAL_STATUSES } from "@/components/features/orders/statusStyles";
import { API_ORIGIN, ApiError } from "@/lib/api/client";
import { fetchOrder } from "@/lib/api/orders";
import type { OrderDetail } from "@/lib/api/types";
import { guestTokenFor } from "./guestTokens";

/** How often to re-read an order when the live connection is unavailable. */
const POLL_MS = 15_000;
const WS_ORIGIN = API_ORIGIN.replace(/^http/, "ws");

type LoadError = "not_found" | "network" | null;

/**
 * An order that keeps itself up to date.
 *
 * Loads once over HTTP (which also answers "not found"), then listens on
 * `ws/orders/{reference}/` for each change. If the socket cannot open or drops,
 * it falls back to polling every 15 seconds — the same endpoint, the same
 * data — so tracking never stops working. A guest proves access with their
 * token in the first message, never in the URL.
 */
export function useLiveOrder(reference: string, enabled: boolean) {
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loadError, setLoadError] = useState<LoadError>(null);
  const [live, setLive] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let finished = false;
    let timer: number | undefined;
    let socket: WebSocket | null = null;

    const accept = (data: OrderDetail) => {
      setOrder(data);
      setLoadError(null);
      if (FINAL_STATUSES.has(data.status)) {
        finished = true;
        socket?.close();
      }
    };

    const poll = async () => {
      if (cancelled || finished) return;
      if (document.visibilityState === "visible") {
        try {
          const data = await fetchOrder(reference);
          if (cancelled) return;
          accept(data);
          if (finished) return;
        } catch (err) {
          if (cancelled) return;
          if (err instanceof ApiError && err.status === 404) {
            setLoadError("not_found");
            return;
          }
          setLoadError((current) => current ?? "network");
        }
      }
      timer = window.setTimeout(poll, POLL_MS);
    };

    const connect = () => {
      if (typeof WebSocket === "undefined") {
        timer = window.setTimeout(poll, POLL_MS);
        return;
      }
      socket = new WebSocket(`${WS_ORIGIN}/ws/orders/${encodeURIComponent(reference)}/`);
      socket.onopen = () => {
        const token = guestTokenFor(reference);
        if (token) socket?.send(JSON.stringify({ type: "auth", token }));
      };
      socket.onmessage = (event) => {
        if (cancelled) return;
        try {
          const message = JSON.parse(String(event.data)) as { type?: string; order?: OrderDetail };
          if (message.type === "order" && message.order) {
            setLive(true);
            accept(message.order);
          }
        } catch {
          /* ignore anything that isn't ours */
        }
      };
      socket.onclose = () => {
        if (cancelled) return;
        setLive(false);
        if (!finished) timer = window.setTimeout(poll, POLL_MS);
      };
    };

    fetchOrder(reference)
      .then((data) => {
        if (cancelled) return;
        accept(data);
        if (!finished) connect();
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setLoadError("not_found");
          return;
        }
        setLoadError("network");
        timer = window.setTimeout(poll, POLL_MS);
      });

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [reference, enabled]);

  return { order, setOrder, loadError, live };
}
