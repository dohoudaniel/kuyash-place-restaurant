"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Phone, MessageCircle, CheckCircle, AlertCircle, Loader2, FileDown, ShoppingCart, CreditCard, XCircle } from "lucide-react";
import { OrderStatus, OrderDetails, OrderSummary } from "@/components/features/orders";
import { ReviewModal } from "@/components/features/reviews";
import { ApiError, api } from "@/lib/api/client";
import { cancelOrder, downloadReceipt, fetchOrder, initialisePayment, reorder } from "@/lib/api/orders";
import { useLiveOrder } from "@/lib/orders/useLiveOrder";
import type { Branch, OrderLine } from "@/lib/api/types";
import { useAuthModalStore } from "@/lib/store/authModalStore";
import { useAuthStore } from "@/lib/store/authStore";
import { useCartStore } from "@/lib/store/cartStore";

const SUBTITLES: Record<string, string> = {
  pending_payment: "Your order is saved and waiting for payment.",
  out_for_delivery: "Your delicious meal is on its way!",
  delivered: "Delivered. Enjoy your meal!",
  ready: "Your order is ready.",
};

function OrderTracking() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const reference = String(params.id);
  const authStatus = useAuthStore((state) => state.status);
  const openAuth = useAuthModalStore((state) => state.open);
  const refreshCart = useCartStore((state) => state.refresh);

  // Live over a WebSocket, polling if that is unavailable.
  const { order, setOrder, loadError, live } = useLiveOrder(reference, authStatus !== "idle" && authStatus !== "loading");
  const [branch, setBranch] = useState<Branch | null>(null);
  const [busy, setBusy] = useState<"pay" | "cancel" | "receipt" | "reorder" | null>(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [confirmReplace, setConfirmReplace] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState<OrderLine | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<Branch>("/core/branch/").then((data) => !cancelled && setBranch(data)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const run = async (kind: NonNullable<typeof busy>, action: () => Promise<void>) => {
    setBusy(kind);
    setActionError(null);
    try {
      await action();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  const pay = () =>
    run("pay", async () => {
      const payment = await initialisePayment(reference);
      window.location.assign(payment.authorization_url);
    });

  const cancel = () =>
    run("cancel", async () => {
      setOrder(await cancelOrder(reference));
      setConfirmCancel(false);
    });

  const receipt = () =>
    run("receipt", async () => {
      const blob = await downloadReceipt(reference);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    });

  // Polling stops once an order is final, so re-read it after a review changes.
  const reloadOrder = () => {
    fetchOrder(reference).then(setOrder).catch(() => undefined);
  };

  const orderAgain = (replace: boolean) =>
    run("reorder", async () => {
      try {
        await reorder(reference, replace);
      } catch (err) {
        if (err instanceof ApiError && err.code === "cart_not_empty") {
          setConfirmReplace(true);
          return;
        }
        throw err;
      }
      await refreshCart();
      router.push("/cart");
    });

  if (loadError === "not_found") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 pt-20" style={{ background: "var(--off-white)" }}>
        <div className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <XCircle className="w-12 h-12 mx-auto mb-4" style={{ color: "var(--text-muted)" }} />
          <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            We couldn&apos;t find that order
          </h1>
          <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
            {authStatus === "authenticated"
              ? "Check the reference in your confirmation email."
              : "If you placed it while signed in, sign in to view it. Otherwise use the link in your confirmation email."}
          </p>
          {authStatus !== "authenticated" && (
            <button
              onClick={() => openAuth("login", `/orders/${reference}`)}
              className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
              style={{ background: "var(--red)" }}
            >
              Sign In
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          {loadError === "network" ? (
            <p role="alert" className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
              We couldn&apos;t load your order. Please check your connection.
            </p>
          ) : (
            <>
              <div className="w-16 h-16 border-4 rounded-full animate-spin mx-auto mb-4"
                style={{ borderColor: "var(--gray-mid)", borderTopColor: "var(--red)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>Loading order details...</p>
            </>
          )}
        </div>
      </div>
    );
  }

  const needsPayment = order.status === "pending_payment" && order.payment_method === "card";
  const banner = searchParams.get("placed")
    ? { tone: "ok" as const, text: "Order placed! We've emailed your confirmation." }
    : searchParams.get("payment") === "retry" && needsPayment
      ? { tone: "warn" as const, text: "Your order is saved, but we couldn't open the payment page. Try again below." }
      : null;

  const actionButton = "w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm transition-all disabled:opacity-50";

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-16">
        <div className="container-custom">
          {/* Back Button */}
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 mb-6 sm:mb-8 text-sm font-semibold transition-colors hover:opacity-70"
            style={{ color: "var(--black)" }}
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          {banner && (
            <div role="status" className="mb-6 p-4 rounded-lg flex items-center gap-3 bg-white border" style={{ borderColor: banner.tone === "ok" ? "#10b981" : "#f59e0b" }}>
              {banner.tone === "ok" ? <CheckCircle className="w-5 h-5" style={{ color: "#10b981" }} /> : <AlertCircle className="w-5 h-5" style={{ color: "#f59e0b" }} />}
              <p className="text-sm font-semibold" style={{ color: "var(--black)" }}>{banner.text}</p>
            </div>
          )}

          {/* Page Header */}
          <div className="mb-8 sm:mb-12">
            <h1 className="font-black text-3xl sm:text-4xl lg:text-5xl mb-3"
              style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Track Your Order
            </h1>
            <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
              {SUBTITLES[order.status] ?? `${order.status_display}. This page updates automatically.`}
              {live && <span className="ml-2 inline-flex items-center gap-1 text-xs font-bold" style={{ color: "#10b981" }}><span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#10b981" }} />Live</span>}
            </p>
          </div>

          {/* Content Grid */}
          <div className="grid lg:grid-cols-3 gap-6 sm:gap-8">
            {/* Left Column - Order Status & Details */}
            <div className="lg:col-span-2 space-y-6 sm:space-y-8">
              <OrderStatus order={order} />
              <OrderDetails order={order} onReview={authStatus === "authenticated" ? setReviewing : undefined} />
            </div>

            {/* Right Column - Order Summary */}
            <div className="space-y-6 sm:space-y-8">
              <OrderSummary order={order} branch={branch} />

              {/* Actions */}
              {(needsPayment || order.can_cancel || order.payment_status === "paid" || (order.status === "delivered" && authStatus === "authenticated")) && (
                <div className="bg-white rounded-xl border p-6 space-y-3" style={{ borderColor: "var(--gray-mid)" }}>
                  {needsPayment && (
                    <button onClick={pay} disabled={busy !== null} className={`${actionButton} text-white hover:opacity-90`} style={{ background: "var(--red)" }}>
                      {busy === "pay" ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                      Pay {order.totals.grand_total.display}
                    </button>
                  )}
                  {order.payment_status === "paid" && (
                    <button onClick={receipt} disabled={busy !== null} className={`${actionButton} hover:bg-gray-50`} style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}>
                      {busy === "receipt" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
                      Download Receipt
                    </button>
                  )}
                  {order.status === "delivered" && authStatus === "authenticated" && (
                    confirmReplace ? (
                      <div className="p-3 rounded-lg" style={{ background: "var(--off-white)" }}>
                        <p className="text-sm mb-2" style={{ color: "var(--black)" }}>Your cart already has items. Replace them with this order?</p>
                        <div className="flex gap-2">
                          <button onClick={() => setConfirmReplace(false)} className="flex-1 py-2 rounded-lg text-sm font-semibold" style={{ border: "2px solid var(--gray-mid)" }}>Keep Cart</button>
                          <button onClick={() => { setConfirmReplace(false); void orderAgain(true); }} className="flex-1 py-2 rounded-lg text-sm font-bold text-white" style={{ background: "var(--red)" }}>Replace</button>
                        </div>
                      </div>
                    ) : (
                      <button onClick={() => orderAgain(false)} disabled={busy !== null} className={`${actionButton} text-white hover:opacity-90`} style={{ background: "var(--red)" }}>
                        {busy === "reorder" ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShoppingCart className="w-4 h-4" />}
                        Order Again
                      </button>
                    )
                  )}
                  {order.can_cancel && (
                    confirmCancel ? (
                      <div className="p-3 rounded-lg" style={{ background: "var(--off-white)" }}>
                        <p className="text-sm mb-2" style={{ color: "var(--black)" }}>Cancel this order?{order.payment_status === "paid" ? " Your payment will be refunded." : ""}</p>
                        <div className="flex gap-2">
                          <button onClick={() => setConfirmCancel(false)} className="flex-1 py-2 rounded-lg text-sm font-semibold" style={{ border: "2px solid var(--gray-mid)" }}>Keep Order</button>
                          <button onClick={cancel} disabled={busy !== null} className="flex-1 py-2 rounded-lg text-sm font-bold text-white disabled:opacity-50" style={{ background: "var(--red)" }}>
                            {busy === "cancel" ? "Cancelling..." : "Yes, Cancel"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button onClick={() => setConfirmCancel(true)} className={`${actionButton} hover:bg-red-50`} style={{ color: "var(--red)" }}>
                        Cancel Order
                      </button>
                    )
                  )}
                  {actionError && <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>{actionError}</p>}
                </div>
              )}

              {/* Contact Support */}
              <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
                <h3 className="font-bold text-base mb-4" style={{ color: "var(--black)" }}>Need Help?</h3>
                <div className="space-y-3">
                  {branch?.phone && (
                    <a
                      href={`tel:${branch.phone}`}
                      className="flex items-center gap-3 p-3 rounded-lg transition-all hover:bg-red-50"
                      style={{ border: "1px solid var(--gray-mid)" }}
                    >
                      <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "rgba(217,4,41,0.1)" }}>
                        <Phone className="w-5 h-5" style={{ color: "var(--red)" }} />
                      </div>
                      <div>
                        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Call us</p>
                        <p className="text-sm font-bold" style={{ color: "var(--black)" }}>{branch.phone}</p>
                      </div>
                    </a>
                  )}

                  <Link
                    href="/contact"
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm text-white transition-all hover:opacity-90"
                    style={{ background: "var(--red)" }}
                  >
                    <MessageCircle className="w-4 h-4" />
                    Contact Support
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <ReviewModal
        key={reviewing?.id ?? "closed"}
        isOpen={reviewing !== null}
        onClose={() => setReviewing(null)}
        itemName={reviewing?.name ?? ""}
        orderLineId={reviewing?.can_review ? reviewing.id : undefined}
        reviewId={reviewing?.review?.id}
        onSaved={reloadOrder}
      />
    </div>
  );
}

export default function OrderTrackingPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
        </div>
      }
    >
      <OrderTracking />
    </Suspense>
  );
}
