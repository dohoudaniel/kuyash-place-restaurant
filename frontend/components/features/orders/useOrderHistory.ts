"use client";

import { useEffect, useState } from "react";
import { fetchMyOrders } from "@/lib/api/orders";
import type { OrderRow } from "@/lib/api/types";

/** The signed-in customer's orders, newest first, with "load more". */
export function useOrderHistory(limit = 20) {
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchMyOrders(null, limit)
      .then((page) => {
        if (cancelled) return;
        setOrders(page.results);
        setNext(page.next);
        setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [limit]);

  const loadMore = async () => {
    if (!next) return;
    setLoadingMore(true);
    try {
      const page = await fetchMyOrders(next);
      setOrders((current) => [...current, ...page.results]);
      setNext(page.next);
    } finally {
      setLoadingMore(false);
    }
  };

  return { orders, state, hasMore: Boolean(next), loadMore, loadingMore };
}
