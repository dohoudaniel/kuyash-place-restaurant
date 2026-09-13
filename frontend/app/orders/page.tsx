"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Package, ShoppingCart, Eye, Loader2, AlertCircle } from "lucide-react";
import { RequireAuth } from "@/components/features/auth";
import { statusStyle, useOrderHistory } from "@/components/features/orders";
import { ApiError } from "@/lib/api/client";
import { mediaUrl } from "@/lib/api/media";
import { reorder } from "@/lib/api/orders";
import { useCartStore } from "@/lib/store/cartStore";

function OrdersPage() {
  const router = useRouter();
  const refreshCart = useCartStore((state) => state.refresh);
  const { orders, state, hasMore, loadMore, loadingMore } = useOrderHistory(20);
  const [reordering, setReordering] = useState<string | null>(null);
  const [replaceFor, setReplaceFor] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ reference: string; text: string; tone: "info" | "error" } | null>(null);

  const handleReorder = async (reference: string, replace = false) => {
    setReordering(reference);
    setNotice(null);
    setReplaceFor(null);
    try {
      // Rebuilt at today's prices; anything no longer on the menu is reported, not re-added.
      const result = await reorder(reference, replace);
      await refreshCart();
      if (result.unavailable.length > 0 || result.changes.length > 0) {
        const unavailable = result.unavailable.map((u) => `${u.name} (${u.reason})`);
        const changed = result.changes.map((c) => c.name);
        setNotice({
          reference,
          tone: "info",
          text: [
            result.message,
            unavailable.length ? `Not added: ${unavailable.join(", ")}.` : "",
            changed.length ? `Price or options changed: ${changed.join(", ")}.` : "",
          ].filter(Boolean).join(" "),
        });
      } else {
        router.push("/cart");
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "cart_not_empty") {
        setReplaceFor(reference);
      } else {
        setNotice({ reference, tone: "error", text: err instanceof ApiError ? err.message : "We couldn't reorder that. Please try again." });
      }
    } finally {
      setReordering(null);
    }
  };

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-16">
        <div className="container-custom">
          {/* Page Header */}
          <div className="mb-8 sm:mb-12">
            <h1
              className="font-black text-3xl sm:text-4xl lg:text-5xl mb-3"
              style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}
            >
              Order History
            </h1>
            {state === "ready" && (
              <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
                {orders.length}{hasMore ? "+" : ""} {orders.length === 1 ? "order" : "orders"} placed
              </p>
            )}
          </div>

          {state === "loading" ? (
            <div className="flex items-center justify-center gap-2 py-24" role="status">
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading your orders…</span>
            </div>
          ) : state === "error" ? (
            <p role="alert" className="text-center py-24 text-sm" style={{ color: "var(--text-muted)" }}>
              We couldn&apos;t load your orders. Please refresh to try again.
            </p>
          ) : orders.length === 0 ? (
            /* Empty State */
            <div className="flex flex-col items-center justify-center py-16 sm:py-24">
              <div
                className="w-24 h-24 sm:w-32 sm:h-32 rounded-full flex items-center justify-center mb-6"
                style={{ background: "rgba(217,4,41,0.1)" }}
              >
                <Package className="w-12 h-12 sm:w-16 sm:h-16" style={{ color: "var(--red)" }} />
              </div>
              <h2
                className="font-black text-2xl sm:text-3xl mb-3"
                style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}
              >
                No orders yet
              </h2>
              <p className="text-sm sm:text-base mb-8 text-center max-w-md" style={{ color: "var(--text-muted)" }}>
                Start your culinary journey by placing your first order
              </p>
              <Link
                href="/menu"
                className="px-8 py-3 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Browse Menu
              </Link>
            </div>
          ) : (
            /* Orders List */
            <div className="space-y-6">
              {orders.map((order) => {
                const { icon: StatusIcon, color } = statusStyle(order.status);
                const shown = order.preview.reduce((count, line) => count + line.quantity, 0);
                const remaining = order.item_count - shown;

                return (
                  <div
                    key={order.reference}
                    className="bg-white rounded-xl border p-6 transition-all hover:shadow-lg"
                    style={{ borderColor: "var(--gray-mid)" }}
                  >
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b mb-4"
                      style={{ borderColor: "var(--gray-mid)" }}>
                      <div>
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-bold text-base" style={{ color: "var(--black)" }}>
                            Order #{order.reference}
                          </h3>
                          <span
                            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                            style={{ background: `color-mix(in srgb, ${color} 12%, transparent)`, color }}
                          >
                            <StatusIcon className="w-3.5 h-3.5" />
                            {order.status_display}
                          </span>
                        </div>
                        {order.placed_at && (
                          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                            Placed on {new Date(order.placed_at).toLocaleDateString("en-NG", {
                              month: "long",
                              day: "numeric",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <Link
                          href={`/orders/${encodeURIComponent(order.reference)}`}
                          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all hover:bg-gray-50"
                          style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </Link>
                        {order.status === "delivered" && (
                          <button
                            onClick={() => handleReorder(order.reference)}
                            disabled={reordering === order.reference}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold text-white transition-all hover:opacity-90 disabled:opacity-50"
                            style={{ background: "var(--red)" }}
                          >
                            {reordering === order.reference ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShoppingCart className="w-4 h-4" />}
                            {reordering === order.reference ? "Adding..." : "Reorder"}
                          </button>
                        )}
                      </div>
                    </div>

                    {replaceFor === order.reference && (
                      <div className="mb-4 p-3 rounded-lg flex flex-col sm:flex-row sm:items-center gap-3" style={{ background: "var(--off-white)" }}>
                        <p className="text-sm flex-1" style={{ color: "var(--black)" }}>Your cart already has items. Replace them with this order?</p>
                        <div className="flex gap-2">
                          <button onClick={() => setReplaceFor(null)} className="px-4 py-2 rounded-lg text-sm font-semibold" style={{ border: "2px solid var(--gray-mid)" }}>Keep Cart</button>
                          <button onClick={() => handleReorder(order.reference, true)} className="px-4 py-2 rounded-lg text-sm font-bold text-white" style={{ background: "var(--red)" }}>Replace</button>
                        </div>
                      </div>
                    )}

                    {notice?.reference === order.reference && (
                      <div role={notice.tone === "error" ? "alert" : "status"} className="mb-4 p-3 rounded-lg flex items-start gap-2" style={{ background: "var(--off-white)" }}>
                        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: notice.tone === "error" ? "var(--red)" : "#f59e0b" }} />
                        <p className="text-sm flex-1" style={{ color: "var(--black)" }}>
                          {notice.text}{" "}
                          {notice.tone === "info" && <Link href="/cart" className="font-bold" style={{ color: "var(--red)" }}>Go to cart →</Link>}
                        </p>
                      </div>
                    )}

                    {/* Items Preview */}
                    <div className="space-y-3 mb-4">
                      {order.preview.map((line, index) => {
                        const imageSrc = mediaUrl(line.image_url);
                        return (
                          <div key={`${line.name}-${index}`} className="flex items-center gap-3">
                            <div
                              className="shrink-0 w-14 h-14 rounded-lg overflow-hidden relative"
                              style={{ background: "var(--cream)" }}
                            >
                              {imageSrc ? (
                                <Image src={imageSrc} alt={line.name} fill sizes="56px" className="object-cover" />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-xl">🍽️</div>
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="font-semibold text-sm truncate" style={{ color: "var(--black)" }}>
                                {line.name}
                              </h4>
                              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                                Qty: {line.quantity}
                              </p>
                            </div>
                            <p className="font-bold text-sm shrink-0" style={{ color: "var(--black)" }}>
                              {line.line_subtotal.display}
                            </p>
                          </div>
                        );
                      })}
                      {remaining > 0 && (
                        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
                          +{remaining} more {remaining === 1 ? "item" : "items"}
                        </p>
                      )}
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: "var(--gray-mid)" }}>
                      <p className="text-xs font-semibold capitalize" style={{ color: "var(--text-muted)" }}>
                        {order.fulfilment_type} · {order.item_count} {order.item_count === 1 ? "item" : "items"}
                      </p>
                      <p className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                        {order.total.display}
                      </p>
                    </div>
                  </div>
                );
              })}

              {hasMore && (
                <div className="text-center">
                  <button
                    onClick={loadMore}
                    disabled={loadingMore}
                    className="px-8 py-3 rounded-full text-sm font-bold transition-all hover:opacity-90 disabled:opacity-50"
                    style={{ border: "2px solid var(--red)", color: "var(--red)", background: "white" }}
                  >
                    {loadingMore ? "Loading..." : "Load Older Orders"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default function GuardedOrdersPage() {
  return (
    <RequireAuth>
      <OrdersPage />
    </RequireAuth>
  );
}
