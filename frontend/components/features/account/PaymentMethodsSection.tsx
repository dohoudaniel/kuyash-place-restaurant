"use client";

import { useEffect, useState } from "react";
import { CreditCard, Trash2, Check, Loader2, ShieldCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api/client";
import type { SavedPaymentMethod } from "@/lib/api/types";

type LoadState = "loading" | "ready" | "error";

function expiryLabel(method: SavedPaymentMethod): string {
  if (!method.card_exp_month || !method.card_exp_year) return "";
  return `${method.card_exp_month.padStart(2, "0")}/${method.card_exp_year.slice(-2)}`;
}

/**
 * Cards the customer chose to keep.
 *
 * Only provider tokens and display fragments exist here. There is no "Add card"
 * form: a card is kept only when the customer asks for it while paying online,
 * and the card details themselves are entered on the provider's hosted page.
 */
export default function PaymentMethodsSection() {
  const [methods, setMethods] = useState<SavedPaymentMethod[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<SavedPaymentMethod[]>("/payments/methods/")
      .then((data) => {
        if (cancelled) return;
        setMethods(data);
        setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const run = async (id: string, action: () => Promise<void>) => {
    setBusyId(id);
    setActionError(null);
    try {
      await action();
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "Something went wrong. Please try again.");
    } finally {
      setBusyId(null);
    }
  };

  const forget = (method: SavedPaymentMethod) =>
    run(method.id, async () => {
      // The response is the remaining list, including any newly promoted default.
      const remaining = await api<SavedPaymentMethod[]>(`/payments/methods/${method.id}/`, { method: "DELETE" });
      setMethods(remaining);
    });

  const makeDefault = (method: SavedPaymentMethod) =>
    run(method.id, async () => {
      const updated = await api<SavedPaymentMethod>(`/payments/methods/${method.id}/set-default/`, { method: "POST" });
      setMethods((previous) => previous.map((m) => ({ ...m, is_default: m.id === updated.id })));
    });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Payment Methods
        </h2>
      </div>

      {state === "loading" && (
        <div className="bg-white rounded-xl border p-8 flex items-center justify-center gap-2" style={{ borderColor: "var(--gray-mid)" }}>
          <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading your saved cards…</span>
        </div>
      )}

      {state === "error" && (
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <p className="text-sm font-semibold" style={{ color: "var(--black)" }}>
            We couldn&apos;t load your saved cards.
          </p>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Please refresh the page to try again.
          </p>
        </div>
      )}

      {state === "ready" && methods.length === 0 && (
        <div className="bg-white rounded-xl border p-8 text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="w-12 h-12 rounded-lg flex items-center justify-center mx-auto mb-3" style={{ background: "var(--gray-light)" }}>
            <CreditCard className="w-6 h-6" style={{ color: "var(--black)" }} />
          </div>
          <p className="font-black text-base" style={{ color: "var(--black)" }}>No saved cards</p>
          <p className="text-sm mt-1 max-w-sm mx-auto" style={{ color: "var(--text-muted)" }}>
            When you pay online, you can choose to keep your card for faster checkout next time.
          </p>
        </div>
      )}

      {actionError && (
        <p role="alert" className="text-sm font-semibold mb-4" style={{ color: "var(--red)" }}>
          {actionError}
        </p>
      )}

      {state === "ready" && methods.length > 0 && (
        <div className="grid sm:grid-cols-2 gap-4">
          {methods.map((method) => {
            const isBusy = busyId === method.id;
            const expiry = expiryLabel(method);

            return (
              <div
                key={method.id}
                className="bg-white rounded-xl border p-5 transition-all hover:shadow-md"
                style={{ borderColor: method.is_default ? "var(--red)" : "var(--gray-mid)", opacity: isBusy ? 0.6 : 1 }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg flex items-center justify-center" style={{ background: "var(--gray-light)" }}>
                      <CreditCard className="w-6 h-6" style={{ color: "var(--black)" }} />
                    </div>
                    <div>
                      <h3 className="font-black text-base capitalize" style={{ color: "var(--black)" }}>
                        {method.card_brand || method.card_label || "Card"}
                      </h3>
                      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                        •••• {method.card_last4}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => forget(method)}
                    disabled={isBusy}
                    aria-label={`Forget card ending ${method.card_last4}`}
                    className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-red-50 disabled:cursor-not-allowed"
                  >
                    {isBusy ? (
                      <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--red)" }} />
                    ) : (
                      <Trash2 className="w-4 h-4" style={{ color: "var(--red)" }} />
                    )}
                  </button>
                </div>

                <div className="flex items-center justify-between pt-4" style={{ borderTop: "1px solid var(--gray-mid)" }}>
                  <p className="text-sm" style={{ color: method.is_expired ? "var(--red)" : "var(--text-muted)" }}>
                    {method.is_expired ? `Expired ${expiry}` : expiry ? `Expires ${expiry}` : ""}
                  </p>
                  {method.is_default ? (
                    <div className="flex items-center gap-1 text-xs font-bold" style={{ color: "var(--red)" }}>
                      <Check className="w-4 h-4" />
                      Default
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => makeDefault(method)}
                      disabled={isBusy}
                      className="text-xs font-bold transition-all hover:opacity-80 disabled:cursor-not-allowed"
                      style={{ color: "var(--black)" }}
                    >
                      Set as Default
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-6 p-4 rounded-lg flex gap-2" style={{ background: "var(--gray-light)" }}>
        <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
          <span style={{ color: "var(--red)" }}>Secure:</span> Your card details are held by our payment partner, not by Kuyash Place. We keep only the last four digits so you can recognise each card.
        </p>
      </div>
    </div>
  );
}
