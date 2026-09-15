"use client";

import { useEffect, useMemo, useState } from "react";
import { Ban, CheckCircle, Loader2, Search, X } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { fetchKitchenItems, setItemAvailability } from "@/lib/api/kds";
import type { KDSItem } from "@/lib/api/types";

/**
 * "86 this dish" — two taps from the board (KDS-E): open this panel, tap the dish.
 * Sold-out dishes are listed first so bringing one back is just as quick.
 */
export default function ItemAvailabilityPanel({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<KDSItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchKitchenItems()
      .then((data) => {
        if (!cancelled) setItems(data.items);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load the menu. Close this and try again.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matching = (items ?? []).filter(
      (item) => !needle || item.name.toLowerCase().includes(needle) || item.category.toLowerCase().includes(needle),
    );
    return [...matching.filter((item) => !item.is_available_now), ...matching.filter((item) => item.is_available_now)];
  }, [items, query]);

  const toggle = async (item: KDSItem) => {
    setSaving(item.slug);
    setError(null);
    try {
      const result = await setItemAvailability(item.slug, !item.is_available_now);
      setItems((current) =>
        (current ?? []).map((existing) =>
          existing.slug === result.slug ? { ...existing, is_available_now: result.is_available_now } : existing,
        ),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That didn't save. Try again.");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="availability-title">
      <button type="button" aria-label="Close" className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white w-full max-w-md h-full flex flex-col shadow-xl">
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: "var(--gray-mid)" }}>
          <h2 id="availability-title" className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Dish availability
          </h2>
          <button type="button" onClick={onClose} className="p-2 rounded-full hover:opacity-70" aria-label="Close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 border-b" style={{ borderColor: "var(--gray-mid)" }}>
          <label className="relative block">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Find a dish"
              className="w-full pl-9 pr-3 py-2.5 rounded-lg border text-sm"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </label>
          <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
            Tap a dish to mark it sold out. Customers stop seeing it straight away.
          </p>
        </div>

        {error && (
          <p className="px-4 pt-3 text-sm" role="alert" style={{ color: "var(--red)" }}>
            {error}
          </p>
        )}

        <ul className="flex-1 overflow-y-auto p-4 flex flex-col gap-2">
          {items === null && !error && (
            <li className="flex items-center gap-2 text-sm" role="status" style={{ color: "var(--text-muted)" }}>
              <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--red)" }} /> Loading dishes…
            </li>
          )}
          {shown.map((item) => (
            <li key={item.slug}>
              <button
                type="button"
                disabled={saving === item.slug}
                onClick={() => toggle(item)}
                className="w-full flex items-center justify-between gap-3 px-4 py-3 rounded-lg border text-left transition-all hover:opacity-80 disabled:opacity-50"
                style={{
                  borderColor: item.is_available_now ? "var(--gray-mid)" : "var(--red)",
                  background: item.is_available_now ? "white" : "rgba(217,4,41,0.06)",
                }}
              >
                <span>
                  <span className="block font-bold text-sm" style={{ color: "var(--black)" }}>{item.name}</span>
                  <span className="block text-xs" style={{ color: "var(--text-muted)" }}>{item.category}</span>
                </span>
                <span
                  className="flex items-center gap-1 text-xs font-bold shrink-0"
                  style={{ color: item.is_available_now ? "#10b981" : "var(--red)" }}
                >
                  {saving === item.slug ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : item.is_available_now ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    <Ban className="w-4 h-4" />
                  )}
                  {item.is_available_now ? "Available" : "Sold out"}
                </span>
              </button>
            </li>
          ))}
          {items !== null && shown.length === 0 && (
            <li className="text-sm" style={{ color: "var(--text-muted)" }}>No dishes match.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
