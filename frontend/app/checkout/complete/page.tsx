"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle, Clock, Loader2, XCircle } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { initialisePayment, verifyPayment } from "@/lib/api/orders";
import { useCartStore } from "@/lib/store/cartStore";

type State = "verifying" | "paid" | "pending" | "failed" | "missing";

/** How long to keep asking while the provider reports "pending". Real polling, not a delay. */
const POLL_INTERVAL_MS = 3000;
const MAX_ATTEMPTS = 10;

/**
 * Where the payment provider sends the customer back.
 *
 * Paystack appends `?reference=`, Flutterwave `?tx_ref=`; both are our own
 * reference. Arriving here proves nothing — the page asks the backend, which asks
 * the provider, and only that answer marks the order paid.
 */
function PaymentComplete() {
  const params = useSearchParams();
  const reference = params.get("reference") ?? params.get("tx_ref") ?? params.get("trxref");
  const refreshCart = useCartStore((state) => state.refresh);

  const [state, setState] = useState<State>(reference ? "verifying" : "missing");
  const [orderReference, setOrderReference] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const started = useRef(false);

  const verify = useCallback(async (ref: string, isCancelled: () => boolean) => {
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
      try {
        const result = await verifyPayment(ref);
        if (isCancelled()) return;
        setOrderReference(result.order_reference);
        if (result.status === "success") {
          setState("paid");
          void refreshCart();
          return;
        }
        if (result.status !== "pending" && result.status !== "initialised") {
          setState("failed");
          return;
        }
      } catch (err) {
        if (isCancelled()) return;
        if (err instanceof ApiError && err.status === 404) {
          setState("missing");
          return;
        }
        if (err instanceof ApiError && err.code === "payment_amount_mismatch") {
          setMessage(err.message);
          setState("failed");
          return;
        }
      }
      await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
      if (isCancelled()) return;
    }
    setState("pending");
  }, [refreshCart]);

  useEffect(() => {
    if (!reference || started.current) return;
    started.current = true;
    let cancelled = false;
    void verify(reference, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [reference, verify]);

  const retryPayment = async () => {
    if (!orderReference) return;
    setRetrying(true);
    setMessage(null);
    try {
      const payment = await initialisePayment(orderReference);
      window.location.assign(payment.authorization_url);
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "We couldn't restart the payment. Please try again.");
      setRetrying(false);
    }
  };

  const card = (icon: React.ReactNode, tone: string, title: string, body: React.ReactNode, actions?: React.ReactNode) => (
    <div className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: tone }}>
        {icon}
      </div>
      <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        {title}
      </h1>
      <div className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>{body}</div>
      {message && (
        <p role="alert" className="text-sm font-semibold mb-4" style={{ color: "var(--red)" }}>{message}</p>
      )}
      {actions && <div className="space-y-3">{actions}</div>}
    </div>
  );

  const primary = "block w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90 disabled:opacity-50";
  const secondary = "block w-full px-6 py-3 rounded-full text-sm font-semibold transition-all hover:bg-gray-50";

  if (state === "verifying") {
    return card(
      <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} />,
      "rgba(217,4,41,0.08)",
      "Confirming your payment",
      <p role="status">We&apos;re checking with the payment provider. This usually takes a few seconds.</p>
    );
  }

  if (state === "paid") {
    return card(
      <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />,
      "#10b98115",
      "Payment confirmed",
      <p>Thank you! Your order is with the kitchen.</p>,
      orderReference && (
        <Link href={`/orders/${encodeURIComponent(orderReference)}`} className={primary} style={{ background: "var(--red)" }}>
          Track Your Order
        </Link>
      )
    );
  }

  if (state === "pending") {
    return card(
      <Clock className="w-8 h-8" style={{ color: "#f59e0b" }} />,
      "#f59e0b15",
      "Still confirming",
      <p>
        The provider hasn&apos;t confirmed your payment yet. You don&apos;t need to pay again — we&apos;ll update your
        order as soon as it clears.
      </p>,
      orderReference && (
        <Link href={`/orders/${encodeURIComponent(orderReference)}`} className={primary} style={{ background: "var(--red)" }}>
          View Your Order
        </Link>
      )
    );
  }

  if (state === "failed") {
    return card(
      <XCircle className="w-8 h-8" style={{ color: "var(--red)" }} />,
      "rgba(217,4,41,0.08)",
      "Payment didn't go through",
      <p>Your order is saved but not paid. You haven&apos;t been charged for this attempt.</p>,
      orderReference && (
        <>
          <button onClick={retryPayment} disabled={retrying} className={primary} style={{ background: "var(--red)" }}>
            {retrying ? "Opening payment..." : "Try Payment Again"}
          </button>
          <Link href={`/orders/${encodeURIComponent(orderReference)}`} className={secondary} style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}>
            View Order
          </Link>
        </>
      )
    );
  }

  return card(
    <XCircle className="w-8 h-8" style={{ color: "var(--text-muted)" }} />,
    "var(--gray-light)",
    "We couldn't find that payment",
    <p>If you were charged, your order will update automatically once the provider notifies us.</p>,
    <Link href="/orders" className={primary} style={{ background: "var(--red)" }}>
      My Orders
    </Link>
  );
}

export default function PaymentCompletePage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 pt-20 sm:pt-24 pb-16" style={{ background: "var(--off-white)" }}>
      <Suspense fallback={<Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} />}>
        <PaymentComplete />
      </Suspense>
    </div>
  );
}
