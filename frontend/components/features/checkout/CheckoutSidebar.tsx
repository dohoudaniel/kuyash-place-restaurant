"use client";

import Image from "next/image";
import { ShoppingBag, Tag, Truck } from "lucide-react";
import { useCartStore } from "@/lib/store/cartStore";
import { usePromoStore } from "@/lib/store/promoStore";

interface CheckoutSidebarProps {
  tip: number;
}

export default function CheckoutSidebar({ tip }: CheckoutSidebarProps) {
  const { items, getTotalPrice, getTotalItems } = useCartStore();
  const { calculateDiscount, appliedPromo } = usePromoStore();

  const subtotal = getTotalPrice();
  const discount = calculateDiscount(subtotal);
  const deliveryFee = appliedPromo?.type === "freeDelivery" ? 0 : 5.0;
  const tax = (subtotal - discount) * 0.075;
  const total = subtotal - discount + deliveryFee + tax + tip;

  return (
    <div className="sticky top-24 space-y-4">
      {/* Order Preview Card */}
      <div className="bg-white rounded-xl border p-5" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-center gap-2 mb-4">
          <ShoppingBag className="w-5 h-5" style={{ color: "var(--red)" }} />
          <h3 className="font-black text-lg" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Order Summary
          </h3>
        </div>

        {/* Items Preview - Show first 3 */}
        <div className="space-y-2 mb-4 max-h-64 overflow-y-auto">
          {items.slice(0, 5).map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-2 p-2 rounded-lg"
              style={{ background: "var(--off-white)" }}
            >
              <div className="shrink-0 w-10 h-10 rounded-lg overflow-hidden relative" style={{ background: "var(--cream)" }}>
                {item.imageKey ? (
                  <Image
                    src={`/assets/menu/${item.imageKey}.png`}
                    alt={item.name}
                    fill
                    className="object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-sm">🍽️</div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold text-xs truncate" style={{ color: "var(--black)" }}>
                  {item.name}
                </h4>
                <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                  {item.quantity}x
                </p>
              </div>
              <p className="font-bold text-xs shrink-0" style={{ color: "var(--red)" }}>
                ₦{(item.price * item.quantity).toFixed(2)}
              </p>
            </div>
          ))}
          {items.length > 5 && (
            <p className="text-xs text-center py-2" style={{ color: "var(--text-muted)" }}>
              +{items.length - 5} more {items.length - 5 === 1 ? "item" : "items"}
            </p>
          )}
        </div>

        {/* Applied Promo */}
        {appliedPromo && discount > 0 && (
          <div className="flex items-center gap-2 p-2 rounded-lg mb-4" style={{ background: "rgba(217,4,41,0.05)" }}>
            <Tag className="w-4 h-4" style={{ color: "var(--red)" }} />
            <div className="flex-1">
              <p className="font-bold text-xs" style={{ color: "var(--black)" }}>{appliedPromo.code}</p>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>-₦{discount.toFixed(2)}</p>
            </div>
          </div>
        )}

        {/* Price Breakdown */}
        <div className="space-y-2 pb-4 mb-4" style={{ borderBottom: "1px solid var(--gray-mid)" }}>
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
          {tip > 0 && (
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--text-muted)" }}>Tip</span>
              <span className="font-semibold" style={{ color: "var(--black)" }}>₦{tip.toFixed(2)}</span>
            </div>
          )}
        </div>

        {/* Total */}
        <div className="flex justify-between items-center">
          <span className="font-bold text-base" style={{ color: "var(--black)" }}>Total</span>
          <span className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
            ₦{total.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Trust Badges */}
      <div className="bg-white rounded-xl border p-4" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-center gap-2 mb-3">
          <Truck className="w-4 h-4" style={{ color: "var(--red)" }} />
          <h4 className="font-bold text-xs" style={{ color: "var(--black)" }}>Delivery Guarantee</h4>
        </div>
        <ul className="space-y-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
          <li className="flex items-start gap-2">
            <span>✓</span>
            <span>Fresh & hot delivery</span>
          </li>
          <li className="flex items-start gap-2">
            <span>✓</span>
            <span>Real-time order tracking</span>
          </li>
          <li className="flex items-start gap-2">
            <span>✓</span>
            <span>100% satisfaction guarantee</span>
          </li>
          <li className="flex items-start gap-2">
            <span>✓</span>
            <span>Secure payment</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
