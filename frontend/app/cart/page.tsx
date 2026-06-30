"use client";

import { useCartStore } from "@/lib/store/cartStore";
import { CartItemCompact, CartSummaryCompact, EmptyCart, SavedForLater, RecommendedItems } from "@/components/features/cart";

export default function CartPage() {
  const { items } = useCartStore();

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-12">
        {items.length === 0 ? (
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
                  {items.length} {items.length === 1 ? "item" : "items"}
                </p>
              </div>
            </div>

            {/* 2-Column Layout */}
            <div className="grid lg:grid-cols-3 gap-6">
              {/* Left: Cart Items (2/3) */}
              <div className="lg:col-span-2 space-y-4">
                {/* Cart Items */}
                <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
                  <div className="space-y-3">
                    {items.map((item) => (
                      <CartItemCompact key={item.id} item={item} />
                    ))}
                  </div>
                </div>

                {/* Saved for Later */}
                <SavedForLater />

                {/* Recommended Items */}
                <RecommendedItems />
              </div>

              {/* Right: Summary (1/3) */}
              <div className="lg:col-span-1">
                <CartSummaryCompact />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
