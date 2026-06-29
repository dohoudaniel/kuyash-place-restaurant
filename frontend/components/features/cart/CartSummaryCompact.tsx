"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Tag, X, Check, ShoppingBag, Truck, Clock } from "lucide-react";
import { useCartStore } from "@/lib/store/cartStore";
import { usePromoStore } from "@/lib/store/promoStore";

export default function CartSummaryCompact() {
  const { getTotalPrice, getTotalItems } = useCartStore();
  const { appliedPromo, applyPromo, removePromo, calculateDiscount, initializePromos, availablePromos } = usePromoStore();

  const [promoCode, setPromoCode] = useState("");
  const [promoMessage, setPromoMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [showPromos, setShowPromos] = useState(false);

  useEffect(() => {
    initializePromos();
  }, [initializePromos]);

  const subtotal = getTotalPrice();
  const discount = calculateDiscount(subtotal);
  const deliveryFee = appliedPromo?.type === "freeDelivery" ? 0 : subtotal > 0 ? 5.00 : 0;
  const tax = (subtotal - discount) * 0.075;
  const total = subtotal - discount + deliveryFee + tax;

  const handleApplyPromo = () => {
    if (!promoCode.trim()) {
      setPromoMessage({ type: "error", text: "Enter a code" });
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

  return (
    <div className="sticky top-24 space-y-4">
      {/* Quick Info Cards */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-lg border p-3 text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <Truck className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
          <p className="text-xs font-bold" style={{ color: "var(--black)" }}>Free Delivery</p>
          <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>on orders $25+</p>
        </div>
        <div className="bg-white rounded-lg border p-3 text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <Clock className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
          <p className="text-xs font-bold" style={{ color: "var(--black)" }}>30-45 mins</p>
          <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>delivery time</p>
        </div>
      </div>

      {/* Main Summary */}
      <div className="bg-white rounded-xl border p-5" style={{ borderColor: "var(--gray-mid)" }}>
        <h2 className="font-black text-lg mb-4 flex items-center gap-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          <ShoppingBag className="w-5 h-5" style={{ color: "var(--red)" }} />
          Order Summary
        </h2>

        {/* Promo Code - Compact */}
        <div className="mb-4 pb-4" style={{ borderBottom: `1px solid var(--gray-mid)` }}>
          {appliedPromo ? (
            <div className="flex items-center justify-between p-2 rounded-lg" style={{ background: "rgba(217,4,41,0.05)" }}>
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4" style={{ color: "var(--red)" }} />
                <div>
                  <p className="font-bold text-xs" style={{ color: "var(--black)" }}>{appliedPromo.code}</p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>-₦{discount.toFixed(2)}</p>
                </div>
              </div>
              <button
                onClick={removePromo}
                className="w-6 h-6 rounded-full flex items-center justify-center transition-all hover:opacity-80"
                style={{ background: "var(--red)" }}
              >
                <X className="w-3 h-3 text-white" />
              </button>
            </div>
          ) : (
            <div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={promoCode}
                  onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === "Enter" && handleApplyPromo()}
                  placeholder="Promo code"
                  className="flex-1 px-3 py-2 text-xs rounded-lg border outline-none transition-colors focus:border-red-500"
                  style={{ borderColor: "var(--gray-mid)" }}
                />
                <button
                  onClick={handleApplyPromo}
                  className="px-3 py-2 rounded-lg text-xs font-bold transition-all hover:opacity-90"
                  style={{ background: "var(--black)", color: "white" }}
                >
                  Apply
                </button>
              </div>

              {promoMessage && (
                <p className={`text-[10px] mt-2 flex items-center gap-1 ${promoMessage.type === "success" ? "text-green-600" : "text-red-600"}`}>
                  {promoMessage.type === "success" ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                  {promoMessage.text}
                </p>
              )}

              {/* Show available promos inline */}
              {!showPromos && availablePromos.length > 0 && (
                <button
                  onClick={() => setShowPromos(true)}
                  className="text-[10px] font-semibold mt-2 transition-colors hover:opacity-70"
                  style={{ color: "var(--red)" }}
                >
                  View {availablePromos.length} available codes
                </button>
              )}

              {showPromos && (
                <div className="mt-2 space-y-1">
                  {availablePromos.slice(0, 3).map((promo) => (
                    <button
                      key={promo.code}
                      onClick={() => {
                        setPromoCode(promo.code);
                        setShowPromos(false);
                      }}
                      className="w-full text-left p-2 rounded text-[10px] transition-all hover:bg-gray-50 flex items-center justify-between"
                      style={{ border: "1px solid var(--gray-mid)" }}
                    >
                      <span className="font-bold">{promo.code}</span>
                      <span style={{ color: "var(--text-muted)" }}>{promo.description.split(" ").slice(0, 3).join(" ")}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Price Breakdown - Compact */}
        <div className="space-y-2 mb-4">
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Subtotal ({getTotalItems()} items)</span>
            <span className="font-semibold" style={{ color: "var(--black)" }}>₦{subtotal.toFixed(2)}</span>
          </div>

          {discount > 0 && (
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--red)" }}>Discount</span>
              <span className="font-semibold" style={{ color: "var(--red)" }}>-₦{discount.toFixed(2)}</span>
            </div>
          )}

          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Delivery</span>
            <span className="font-semibold" style={{ color: deliveryFee > 0 ? "var(--black)" : "var(--red)" }}>
              {deliveryFee > 0 ? `₦${deliveryFee.toFixed(2)}` : "FREE"}
            </span>
          </div>

          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Tax</span>
            <span className="font-semibold" style={{ color: "var(--black)" }}>₦{tax.toFixed(2)}</span>
          </div>

          <div className="h-px" style={{ background: "var(--gray-mid)" }} />

          <div className="flex justify-between items-center pt-1">
            <span className="font-bold text-sm" style={{ color: "var(--black)" }}>Total</span>
            <span className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
              ₦{total.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-2">
          <Link
            href="/checkout"
            className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-[1.02]"
            style={{ background: "var(--red)", boxShadow: "0 4px 14px rgba(217,4,41,0.3)" }}
          >
            Proceed to Checkout
          </Link>

          <Link
            href="/#menu"
            className="w-full flex items-center justify-center px-6 py-2.5 rounded-full text-xs font-semibold transition-all duration-200 hover:bg-gray-50"
            style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
          >
            Continue Shopping
          </Link>
        </div>

        {/* Security badges */}
        <div className="flex items-center justify-center gap-3 mt-4 pt-4" style={{ borderTop: `1px solid var(--gray-mid)` }}>
          <div className="text-center">
            <p className="text-[10px] font-semibold" style={{ color: "var(--text-muted)" }}>🔒 Secure Checkout</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] font-semibold" style={{ color: "var(--text-muted)" }}>✓ SSL Encrypted</p>
          </div>
        </div>
      </div>
    </div>
  );
}
