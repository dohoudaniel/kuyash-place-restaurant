"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Ban, Bell, BellOff, ChefHat, Loader2, Lock, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { fetchKitchenSummary, fetchRiders } from "@/lib/api/kds";
import type { KDSRider, KDSSummary, KDSTicket } from "@/lib/api/types";
import { useKitchenQueue } from "@/lib/kitchen/useKitchenQueue";
import ItemAvailabilityPanel from "./ItemAvailabilityPanel";
import TicketCard from "./TicketCard";

const COLUMNS: { key: string; title: string; statuses: string[] }[] = [
  { key: "new", title: "New", statuses: ["paid"] },
  { key: "cooking", title: "Cooking", statuses: ["confirmed", "preparing"] },
  { key: "ready", title: "Ready", statuses: ["ready"] },
  { key: "out", title: "Out for delivery", statuses: ["out_for_delivery"] },
];

/** A short two-note chime for a new ticket (KDS-G). Browsers only allow sound after a tap. */
function useChime() {
  const context = useRef<AudioContext | null>(null);
  const [enabled, setEnabled] = useState(false);

  const enable = useCallback(() => {
    context.current ??= new AudioContext();
    void context.current.resume();
    setEnabled(true);
  }, []);

  const play = useCallback(() => {
    const audio = context.current;
    if (!enabled || !audio) return;
    [0, 0.2].forEach((offset, index) => {
      const start = audio.currentTime + offset;
      const oscillator = audio.createOscillator();
      const gain = audio.createGain();
      oscillator.frequency.value = index === 0 ? 880 : 1175;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.35, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.18);
      oscillator.connect(gain).connect(audio.destination);
      oscillator.start(start);
      oscillator.stop(start + 0.2);
    });
  }, [enabled]);

  return { enabled, enable, disable: () => setEnabled(false), play };
}

/**
 * The Kitchen Display System: one screen the kitchen keeps open during service.
 *
 * Tickets run oldest first across four columns, with an elapsed timer that turns
 * red when an order is late. Live over a WebSocket, with a polling fallback and
 * a stale banner that keeps the last tickets on screen if the connection drops.
 */
export default function KitchenBoard() {
  const chime = useChime();
  const { tickets, reasons, load, live, stale, updatedAt, upsert, reload } = useKitchenQueue(chime.play);
  const [now, setNow] = useState(() => Date.now());
  const [summary, setSummary] = useState<KDSSummary | null>(null);
  const [riders, setRiders] = useState<KDSRider[]>([]);
  const [showAvailability, setShowAvailability] = useState(false);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (load !== "ready") return;
    let cancelled = false;
    fetchKitchenSummary()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        /* the board works without the header figures */
      });
    return () => {
      cancelled = true;
    };
  }, [load, updatedAt]);

  useEffect(() => {
    if (load !== "ready") return;
    let cancelled = false;
    const loadRiders = () =>
      fetchRiders()
        .then((data) => {
          if (!cancelled) setRiders(data.riders);
        })
        .catch(() => {
          /* assignment is optional; the button simply doesn't show */
        });
    void loadRiders();
    const id = window.setInterval(loadRiders, 5 * 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [load]);

  const closeAvailability = useCallback(() => setShowAvailability(false), []);

  if (load === "forbidden") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ background: "var(--off-white)" }}>
        <div className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "rgba(217,4,41,0.08)" }}>
            <Lock className="w-6 h-6" style={{ color: "var(--red)" }} />
          </div>
          <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Kitchen staff only
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            This screen is for the kitchen team. Ask a manager to add your account to the kitchen group.
          </p>
        </div>
      </div>
    );
  }

  if (load === "loading" || (load === "error" && updatedAt === null)) {
    return (
      <div className="min-h-screen flex items-center justify-center gap-2" style={{ background: "var(--off-white)" }} role="status">
        {load === "loading" ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Opening the kitchen display…</span>
          </>
        ) : (
          <>
            <WifiOff className="w-5 h-5" style={{ color: "var(--red)" }} />
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Can&apos;t reach the server. Retrying every 10 seconds…</span>
          </>
        )}
      </div>
    );
  }

  const revenue = summary?.todays_revenue as { display?: string } | undefined;

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--off-white)" }}>
      <header className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 py-3" style={{ background: "var(--black)" }}>
        <div className="flex items-center gap-3">
          <ChefHat className="w-7 h-7" style={{ color: "var(--red)" }} />
          <h1 className="font-black text-xl sm:text-2xl text-white" style={{ fontFamily: "var(--font-playfair)" }}>
            Kitchen
          </h1>
          <span
            className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full"
            style={{ background: live ? "rgba(16,185,129,0.2)" : "rgba(245,158,11,0.2)", color: live ? "#6ee7b7" : "#fcd34d" }}
          >
            {live ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {live ? "Live" : "Checking every 10s"}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm text-white">
          {summary && (
            <span className="px-3 py-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.1)" }}>
              {summary.open_tickets} open{revenue?.display ? ` · Today ${revenue.display}` : ""}
            </span>
          )}
          <button
            type="button"
            onClick={chime.enabled ? chime.disable : chime.enable}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full font-bold transition-all hover:opacity-90"
            style={{ background: chime.enabled ? "rgba(255,255,255,0.1)" : "var(--red)" }}
          >
            {chime.enabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
            {chime.enabled ? "Sound on" : "Turn sound on"}
          </button>
          <button
            type="button"
            onClick={() => setShowAvailability(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full font-bold transition-all hover:opacity-90"
            style={{ background: "rgba(255,255,255,0.1)" }}
          >
            <Ban className="w-4 h-4" /> Sold out
          </button>
          <button
            type="button"
            onClick={reload}
            className="p-2 rounded-full transition-all hover:opacity-90"
            style={{ background: "rgba(255,255,255,0.1)" }}
            aria-label="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {stale && (
        <p className="px-4 sm:px-6 py-2 text-sm font-bold flex items-center gap-2" role="status" style={{ background: "#fef3c7", color: "#92400e" }}>
          <WifiOff className="w-4 h-4" />
          Connection lost — showing the tickets from{" "}
          {updatedAt ? new Date(updatedAt).toLocaleTimeString("en-NG", { hour: "2-digit", minute: "2-digit" }) : "earlier"}. Reconnecting…
        </p>
      )}

      <main className="flex-1 grid gap-4 p-4 sm:p-6 md:grid-cols-2 xl:grid-cols-4 items-start">
        {COLUMNS.map((column) => {
          const inColumn = tickets.filter((ticket: KDSTicket) => column.statuses.includes(ticket.status));
          return (
            <section key={column.key} aria-labelledby={`column-${column.key}`} className="flex flex-col gap-3">
              <h2 id={`column-${column.key}`} className="font-black text-lg flex items-center justify-between" style={{ color: "var(--black)" }}>
                {column.title}
                <span className="text-sm font-bold px-2.5 py-0.5 rounded-full text-white" style={{ background: inColumn.length ? "var(--red)" : "var(--gray-mid)" }}>
                  {inColumn.length}
                </span>
              </h2>
              {inColumn.length === 0 ? (
                <p className="text-sm rounded-xl border border-dashed p-6 text-center" style={{ borderColor: "var(--gray-mid)", color: "var(--text-muted)" }}>
                  Nothing here
                </p>
              ) : (
                inColumn.map((ticket) => (
                  <TicketCard
                    key={ticket.reference}
                    ticket={ticket}
                    now={now}
                    reasons={reasons}
                    riders={riders}
                    onUpdated={upsert}
                    onReload={reload}
                  />
                ))
              )}
            </section>
          );
        })}
      </main>

      {showAvailability && <ItemAvailabilityPanel onClose={closeAvailability} />}
    </div>
  );
}
