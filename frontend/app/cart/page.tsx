"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { api } from "@/lib/api/client";
import type { Branch } from "@/lib/api/types";
import { useCartStore } from "@/lib/store/cartStore";
import { CartItemCompact, CartSummaryCompact, EmptyCart, SavedForLater, RecommendedItems } from "@/components/features/cart";

export default function CartPage() {
  const cart = useCartStore((state) => state.cart);
  const status = useCartStore((state) => state.status);
  const [branch, setBranch] = useState<Branch | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<Branch>("/core/branch/")
      .then((data) => {
        if (!cancelled) setBranch(data);
      })
      .catch(() => {
        /* the summary omits branch facts it cannot show */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const isLoading = (status === "idle" || status === "loading") && !cart;

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-12">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 py-24" role="status">
            <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading your cart…</span>
          </div>
        ) : status === "error" && !cart ? (
          <p role="alert" className="text-center py-24 text-sm" style={{ color: "var(--text-muted)" }}>
            We couldn&apos;t load your cart. Please refresh to try again.
          </p>
        ) : !cart || cart.items.length === 0 ? (
          <EmptyCart />
        ) : (
          <div className="container-custom">
            {/* Compact Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="font-black text-2xl sm:text-3xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                  Shopping Cart
                </h1>
                <p className="text-xs sm:text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                  {cart.item_count} {cart.item_count === 1 ? "item" : "items"}
                </p>
              </div>
            </div>

            {/* 2-Column Layout */}
            <div className="grid lg:grid-cols-3 gap-6">
              {/* Left: Cart Items (2/3) */}
              <div className="lg:col-span-2 space-y-4">
                {/* What changed since these were added — the old cart could not detect either. */}
                {(cart.changes.length > 0 || cart.unavailable.length > 0) && (
                  <div role="status" className="bg-white rounded-xl border p-4 space-y-2" style={{ borderColor: "#fcd34d" }}>
                    {cart.unavailable.map((entry) => (
                      <p key={`u-${entry.item}`} className="flex items-start gap-2 text-sm" style={{ color: "var(--black)" }}>
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
                        <span><strong>{entry.name}</strong> — {entry.reason}</span>
                      </p>
                    ))}
                    {cart.changes.map((change) => (
                      <p key={`c-${change.item}-${change.type}`} className="flex items-start gap-2 text-sm" style={{ color: "var(--black)" }}>
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#f59e0b" }} />
                        <span>
                          The price of <strong>{change.name}</strong> {change.type === "price_increased" ? "went up" : "went down"}
                          {change.old && change.new ? ` from ${change.old.display} to ${change.new.display}` : ""}.
                        </span>
                      </p>
                    ))}
                  </div>
                )}

                {/* Cart Items */}
                <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
                  <div className="space-y-3">
                    {cart.items.map((line) => (
                      <CartItemCompact key={line.id} line={line} />
                    ))}
                  </div>
                </div>

                {/* Saved for Later */}
                <SavedForLater />

                {/* Recommended Items */}
                <RecommendedItems excludeSlugs={cart.items.map((line) => line.menu_item.slug)} />
              </div>

              {/* Right: Summary (1/3) */}
              <div className="lg:col-span-1">
                <CartSummaryCompact cart={cart} branch={branch} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
