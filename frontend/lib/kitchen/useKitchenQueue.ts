"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_ORIGIN, ApiError } from "@/lib/api/client";
import { fetchKitchenQueue } from "@/lib/api/kds";
import type { KDSRejectReason, KDSTicket } from "@/lib/api/types";

/** How often to re-read the queue while the live connection is down. */
const POLL_MS = 10_000;
/** A quiet re-read while live, so late flags and missed pushes catch up. */
const REFRESH_MS = 60_000;
/** How long to wait before trying the live connection again. */
const RECONNECT_MS = 30_000;
const WS_ORIGIN = API_ORIGIN.replace(/^http/, "ws");

export const KITCHEN_STATUSES = ["paid", "confirmed", "preparing", "ready", "out_for_delivery"] as const;
const ON_SCREEN = new Set<string>(KITCHEN_STATUSES);

export type KitchenLoad = "loading" | "ready" | "forbidden" | "error";

const oldestFirst = (a: KDSTicket, b: KDSTicket) => Date.parse(a.placed_at) - Date.parse(b.placed_at);

/**
 * The kitchen's ticket queue, kept live.
 *
 * Loads over HTTP, then listens on `ws/kds/`. If the socket cannot open or
 * drops, it polls every 10 seconds and keeps showing the last tickets it had,
 * flagged stale — never a blank screen mid-service (KDS-H). `onNewTicket`
 * fires for each newly paid order after the first load, for the chime (KDS-G).
 */
export function useKitchenQueue(onNewTicket: (ticket: KDSTicket) => void) {
  const [tickets, setTickets] = useState<KDSTicket[]>([]);
  const [reasons, setReasons] = useState<KDSRejectReason[]>([]);
  const [load, setLoad] = useState<KitchenLoad>("loading");
  const [live, setLive] = useState(false);
  const [stale, setStale] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);

  const seen = useRef<Set<string> | null>(null);
  const notify = useRef(onNewTicket);
  const reloadRef = useRef<() => Promise<boolean>>(async () => true);

  useEffect(() => {
    notify.current = onNewTicket;
  }, [onNewTicket]);

  const replace = useCallback((next: KDSTicket[]) => {
    const known = seen.current;
    if (known) {
      for (const ticket of next) {
        if (!known.has(ticket.reference) && ticket.status === "paid") notify.current(ticket);
      }
    }
    seen.current = new Set(next.map((ticket) => ticket.reference));
    setTickets([...next].sort(oldestFirst));
    setUpdatedAt(Date.now());
    setStale(false);
  }, []);

  /** Put one ticket in place, or take it off the board once it has left the kitchen. */
  const upsert = useCallback((ticket: KDSTicket) => {
    const known = seen.current ?? new Set<string>();
    if (!known.has(ticket.reference) && ticket.status === "paid") notify.current(ticket);
    known.add(ticket.reference);
    seen.current = known;
    setTickets((current) => {
      const rest = current.filter((existing) => existing.reference !== ticket.reference);
      return ON_SCREEN.has(ticket.status) ? [...rest, ticket].sort(oldestFirst) : rest;
    });
    setUpdatedAt(Date.now());
  }, []);

  useEffect(() => {
    let cancelled = false;
    let connected = false;
    let loop = 0;
    let timer: number | undefined;
    let retry: number | undefined;
    let socket: WebSocket | null = null;

    /** Read the queue. Returns false only when this person has no kitchen access. */
    const read = async (): Promise<boolean> => {
      try {
        const queue = await fetchKitchenQueue();
        if (cancelled) return true;
        setReasons(queue.reject_reasons);
        replace(queue.orders);
        setLoad("ready");
        return true;
      } catch (err) {
        if (cancelled) return true;
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setLoad("forbidden");
          return false;
        }
        setStale(true);
        setLoad((current) => (current === "loading" ? "error" : current));
        return true;
      }
    };
    reloadRef.current = read;

    const startPolling = () => {
      const id = ++loop;
      const tick = async () => {
        if (cancelled || connected || id !== loop) return;
        const allowed = await read();
        if (allowed && !cancelled && !connected && id === loop) timer = window.setTimeout(tick, POLL_MS);
      };
      window.clearTimeout(timer);
      timer = window.setTimeout(tick, POLL_MS);
    };

    const connect = () => {
      if (cancelled) return;
      if (typeof WebSocket === "undefined") {
        startPolling();
        return;
      }
      socket = new WebSocket(`${WS_ORIGIN}/ws/kds/`);
      socket.onmessage = (event) => {
        if (cancelled) return;
        try {
          const message = JSON.parse(String(event.data)) as { type?: string; orders?: KDSTicket[]; ticket?: KDSTicket };
          if (message.type === "queue" && message.orders) {
            connected = true;
            loop++; // stop any polling loop
            window.clearTimeout(timer);
            setLive(true);
            replace(message.orders);
          } else if (message.type === "ticket" && message.ticket) {
            upsert(message.ticket);
          }
        } catch {
          /* ignore anything that isn't ours */
        }
      };
      socket.onclose = () => {
        if (cancelled) return;
        connected = false;
        setLive(false);
        setStale(true);
        startPolling();
        window.clearTimeout(retry);
        retry = window.setTimeout(connect, RECONNECT_MS);
      };
    };

    const refresh = window.setInterval(() => {
      if (connected && document.visibilityState === "visible") void read();
    }, REFRESH_MS);

    void read().then((allowed) => {
      if (allowed && !cancelled) connect();
    });

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      window.clearTimeout(retry);
      window.clearInterval(refresh);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [replace, upsert]);

  const reload = useCallback(() => {
    void reloadRef.current();
  }, []);

  return { tickets, reasons, load, live, stale, updatedAt, upsert, reload };
}
