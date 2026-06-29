"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Tag, X, Check } from "lucide-react";
import { useCartStore } from "@/lib/store/cartStore";
import { usePromoStore } from "@/lib/store/promoStore";

export default function CartSummary() {
  const { getTotalPrice, getTotalItems } = useCartStore();
  const { appliedPromo, applyPromo, removePromo, calculateDiscount, initializePromos } = usePromoStore();

  const [promoCode, setPromoCode] = useState("");
  const [promoMessage, setPromoMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    initializePromos();
  }, [initializePromos]);

  const subtotal = getTotalPrice();
  const discount = calculateDiscount(subtotal);
  const deliveryFee = appliedPromo?.type === "freeDelivery" ? 0 : subtotal > 0 ? 5.00 : 0;
  const tax = (subtotal - discount) * 0.075; // 7.5% VAT
  const total = subtotal - discount + deliveryFee + tax;

  const handleApplyPromo = () => {
    if (!promoCode.trim()) {
      setPromoMessage({ type: "error", text: "Please enter a promo code" });
      return;
    }

    const result = applyPromo(promoCode, subtotal);

    if (result.success) {
      setPromoMessage({ type: "success", text: result.message });
      setPromoCode("");
      setTimeout(() => setPromoMessage(null), 3000);
    } else {
      setPromoMessage({ type: "error", text: result.message });
    }
  };

  const handleRemovePromo = () => {
    removePromo();
    setPromoMessage(null);
  };

  return (
    <div className="bg-white rounded-xl border p-6 sticky top-24" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-lg mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Order Summary
      </h2>

      <div className="space-y-3 mb-6">
        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>Subtotal ({getTotalItems()} items)</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>₦{subtotal.toFixed(2)}</span>
        </div>

        {discount > 0 && (
          <div className="flex justify-between text-sm">
            <span style={{ color: "var(--red)" }}>Discount ({appliedPromo?.code})</span>
            <span className="font-semibold" style={{ color: "var(--red)" }}>-₦{discount.toFixed(2)}</span>
          </div>
        )}

        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>Delivery Fee</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>
            {deliveryFee > 0 ? `₦${deliveryFee.toFixed(2)}` : <span style={{ color: "var(--red)" }}>Free</span>}
          </span>
        </div>

        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>Tax (7.5%)</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>₦{tax.toFixed(2)}</span>
        </div>

        <div className="h-px" style={{ background: "var(--gray-mid)" }} />

        <div className="flex justify-between pt-2">
          <span className="font-bold text-base" style={{ color: "var(--black)" }}>Total</span>
          <span className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
            ₦{total.toFixed(2)}
          </span>
        </div>
      </div>

      <Link
        href="/checkout"
        className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
        style={{ background: "var(--red)" }}
      >
        Proceed to Checkout
      </Link>

      <Link
        href="/#menu"
        className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm font-semibold transition-all duration-200 hover:bg-gray-50 mt-3"
        style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
      >
        Continue Shopping
      </Link>

      {/* Promo Code */}
      <div className="mt-6 pt-6" style={{ borderTop: `1px solid var(--gray-mid)` }}>
        <label className="text-xs font-bold uppercase tracking-wide mb-2 block flex items-center gap-2" style={{ color: "var(--black)" }}>
          <Tag className="w-4 h-4" style={{ color: "var(--red)" }} />
          Promo Code
        </label>

        {appliedPromo ? (
          <div className="flex items-center justify-between p-3 rounded-lg" style={{ background: "rgba(217,4,41,0.05)", border: "1px solid var(--red)" }}>
            <div>
              <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{appliedPromo.code}</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{appliedPromo.description}</p>
            </div>
            <button
              onClick={handleRemovePromo}
              className="w-7 h-7 rounded-full flex items-center justify-center transition-all hover:opacity-80"
              style={{ background: "var(--red)" }}
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        ) : (
          <>
            <div className="flex gap-2">
              <input
                type="text"
                value={promoCode}
                onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && handleApplyPromo()}
                placeholder="Enter code"
                className="flex-1 px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
                style={{ borderColor: "var(--gray-mid)" }}
              />
              <button
                onClick={handleApplyPromo}
                className="px-4 py-2 rounded-lg text-sm font-bold transition-all hover:opacity-90"
                style={{ background: "var(--black)", color: "white" }}
              >
                Apply
              </button>
            </div>

            {promoMessage && (
              <div
                className="flex items-start gap-2 mt-3 p-2 rounded-lg text-xs"
                style={{
                  background: promoMessage.type === "success" ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
                  color: promoMessage.type === "success" ? "#16a34a" : "#dc2626",
                }}
              >
                {promoMessage.type === "success" ? (
                  <Check className="w-4 h-4 shrink-0 mt-0.5" />
                ) : (
                  <X className="w-4 h-4 shrink-0 mt-0.5" />
                )}
                <p>{promoMessage.text}</p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Available Promos Hint */}
      {!appliedPromo && (
        <details className="mt-4">
          <summary className="text-xs font-semibold cursor-pointer" style={{ color: "var(--text-muted)" }}>
            View available promo codes
          </summary>
          <div className="mt-3 space-y-2">
            {["WELCOME10", "SAVE500", "FREEDEL", "MEGA20"].map((code) => (
              <button
                key={code}
                onClick={() => setPromoCode(code)}
                className="w-full text-left p-2 rounded-lg text-xs font-mono transition-all hover:bg-gray-50"
                style={{ border: "1px solid var(--gray-mid)" }}
              >
                {code}
              </button>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
