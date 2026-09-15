"use client";

import { useState } from "react";
import { AlertTriangle, Banknote, Bike, Clock, Loader2, ShoppingBag, StickyNote } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { acceptTicket, advanceTicket, assignRider, rejectTicket, type KitchenAdvanceTarget } from "@/lib/api/kds";
import type { KDSRejectReason, KDSRider, KDSTicket } from "@/lib/api/types";

interface TicketCardProps {
  ticket: KDSTicket;
  /** Milliseconds since the epoch, ticking once a second. */
  now: number;
  reasons: KDSRejectReason[];
  riders: KDSRider[];
  onUpdated: (ticket: KDSTicket) => void;
  /** Re-read the queue — after changes the API does not return as a ticket. */
  onReload: () => void;
}

function elapsedLabel(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = String(seconds % 60).padStart(2, "0");
  return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes}:${rest}`;
}

/**
 * One kitchen ticket.
 *
 * Modifiers and special instructions are the loudest thing on the card (KDS-5):
 * they are what the kitchen actually cooks from. Every move is a single tap
 * (KDS-C); rejecting asks for a reason from the fixed list (KDS-D).
 */
export default function TicketCard({ ticket, now, reasons, riders, onUpdated, onReload }: TicketCardProps) {
  const [busy, setBusy] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [riderId, setRiderId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const elapsed = Math.max(0, Math.floor((now - Date.parse(ticket.placed_at)) / 1000));
  const isDelivery = ticket.fulfilment_type === "delivery";
  const accent = ticket.is_late ? "var(--red)" : "var(--gray-mid)";

  const run = async (action: () => Promise<KDSTicket | unknown>, reload = false) => {
    setBusy(true);
    setError(null);
    try {
      const result = await action();
      if (reload) onReload();
      else onUpdated(result as KDSTicket);
      setRejecting(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That didn't go through. Check the connection and try again.");
    } finally {
      setBusy(false);
    }
  };

  const advance = (to: KitchenAdvanceTarget) => run(() => advanceTicket(ticket.reference, to));

  const primary = "flex-1 px-4 py-3 rounded-full font-bold text-white text-sm transition-all hover:opacity-90 disabled:opacity-50";
  const secondary = "px-4 py-3 rounded-full font-bold text-sm border transition-all hover:opacity-80 disabled:opacity-50";

  return (
    <article
      className="bg-white rounded-xl border-2 p-4 flex flex-col gap-3"
      style={{ borderColor: accent }}
      aria-label={`Order ${ticket.reference}`}
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="font-black text-lg leading-tight" style={{ color: "var(--black)" }}>
            {ticket.reference}
          </p>
          <p className="text-xs flex items-center gap-1 mt-1" style={{ color: "var(--text-muted)" }}>
            {isDelivery ? <Bike className="w-3.5 h-3.5" /> : <ShoppingBag className="w-3.5 h-3.5" />}
            {isDelivery ? `Delivery${ticket.zone ? ` · ${ticket.zone}` : ""}` : "Pickup"}
            {ticket.customer.name ? ` · ${ticket.customer.name}` : ""}
          </p>
        </div>
        <div
          className="flex items-center gap-1 font-black text-lg tabular-nums"
          style={{ color: ticket.is_late ? "var(--red)" : "var(--black)" }}
          title={ticket.is_late ? "Past its estimated ready time" : "Time since the order was placed"}
        >
          {ticket.is_late ? <AlertTriangle className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
          {elapsedLabel(elapsed)}
        </div>
      </header>

      {ticket.requires_cash_collection && (
        <p
          className="text-sm font-bold rounded-lg px-3 py-2 flex items-center gap-2"
          style={{ background: "rgba(245,158,11,0.15)", color: "#92400e" }}
        >
          <Banknote className="w-4 h-4" />
          Cash on delivery — collect {ticket.grand_total.display}
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {ticket.items.map((line, index) => (
          <li key={`${line.name}-${index}`}>
            <p className="font-bold text-base" style={{ color: "var(--black)" }}>
              {line.quantity}× {line.name}
              {line.variant ? <span className="font-normal"> ({line.variant})</span> : null}
            </p>
            {line.modifiers.length > 0 && (
              <p className="text-base font-black" style={{ color: "var(--red)" }}>
                + {line.modifiers.join(", ")}
              </p>
            )}
            {line.special_instructions && (
              <p className="text-base font-black rounded-md px-2 py-1 mt-1" style={{ background: "rgba(217,4,41,0.08)", color: "var(--red)" }}>
                “{line.special_instructions}”
              </p>
            )}
          </li>
        ))}
      </ul>

      {ticket.customer_note && (
        <p className="text-sm rounded-lg px-3 py-2 flex gap-2" style={{ background: "var(--off-white)", color: "var(--black)" }}>
          <StickyNote className="w-4 h-4 shrink-0 mt-0.5" />
          {ticket.customer_note}
        </p>
      )}

      {ticket.rider && (
        <p className="text-sm flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
          <Bike className="w-4 h-4" /> Rider: <strong style={{ color: "var(--black)" }}>{ticket.rider.name}</strong>
        </p>
      )}

      {error && (
        <p className="text-sm font-medium" role="alert" style={{ color: "var(--red)" }}>
          {error}
        </p>
      )}

      {rejecting ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-bold" style={{ color: "var(--black)" }}>Why can&apos;t the kitchen take it?</p>
          {reasons.map((reason) => (
            <button
              key={reason.code}
              type="button"
              disabled={busy}
              onClick={() => run(() => rejectTicket(ticket.reference, reason.code))}
              className="text-left px-4 py-2.5 rounded-lg border text-sm font-medium transition-all hover:opacity-80 disabled:opacity-50"
              style={{ borderColor: "var(--gray-mid)", color: "var(--black)" }}
            >
              {reason.title}
            </button>
          ))}
          <button type="button" disabled={busy} onClick={() => setRejecting(false)} className={secondary} style={{ borderColor: "var(--gray-mid)", color: "var(--black)" }}>
            Keep the order
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 items-center">
          {busy && <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />}

          {ticket.status === "paid" && (
            <>
              <button type="button" disabled={busy} onClick={() => run(() => acceptTicket(ticket.reference))} className={primary} style={{ background: "var(--red)" }}>
                Accept
              </button>
              <button type="button" disabled={busy} onClick={() => setRejecting(true)} className={secondary} style={{ borderColor: "var(--gray-mid)", color: "var(--black)" }}>
                Reject
              </button>
            </>
          )}

          {ticket.status === "confirmed" && (
            <button type="button" disabled={busy} onClick={() => advance("preparing")} className={primary} style={{ background: "var(--red)" }}>
              Start cooking
            </button>
          )}

          {ticket.status === "preparing" && (
            <button type="button" disabled={busy} onClick={() => advance("ready")} className={primary} style={{ background: "var(--red)" }}>
              Mark ready
            </button>
          )}

          {ticket.status === "ready" && !isDelivery && (
            <button type="button" disabled={busy} onClick={() => advance("delivered")} className={primary} style={{ background: "#10b981" }}>
              Collected
            </button>
          )}

          {ticket.status === "ready" && isDelivery && (
            <div className="flex flex-col gap-2 w-full">
              {riders.length > 0 && (
                <div className="flex gap-2">
                  <select
                    aria-label="Rider"
                    value={riderId}
                    onChange={(event) => setRiderId(event.target.value)}
                    className="flex-1 min-w-0 px-3 py-2.5 rounded-lg border text-sm bg-white"
                    style={{ borderColor: "var(--gray-mid)", color: "var(--black)" }}
                  >
                    <option value="">{ticket.rider ? "Change rider…" : "Choose a rider…"}</option>
                    {riders.map((rider) => (
                      <option key={rider.id} value={rider.id}>
                        {rider.name}
                        {rider.is_on_shift ? "" : " (off shift)"}
                        {rider.zone ? ` · ${rider.zone}` : ""}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={busy || !riderId}
                    onClick={() => run(() => assignRider(ticket.reference, riderId), true)}
                    className={secondary}
                    style={{ borderColor: "var(--gray-mid)", color: "var(--black)" }}
                  >
                    Assign
                  </button>
                </div>
              )}
              <button type="button" disabled={busy} onClick={() => advance("out_for_delivery")} className={primary} style={{ background: "#3b82f6" }}>
                Out for delivery
              </button>
            </div>
          )}

          {ticket.status === "out_for_delivery" && (
            <button type="button" disabled={busy} onClick={() => advance("delivered")} className={primary} style={{ background: "#10b981" }}>
              Delivered
            </button>
          )}
        </div>
      )}
    </article>
  );
}
