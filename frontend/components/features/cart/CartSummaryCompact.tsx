"use client";

import { useState } from "react";
import Link from "next/link";
import { Tag, X, Check, ShoppingBag, Truck, Clock, AlertCircle, Loader2, Gift } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import type { Branch, Cart } from "@/lib/api/types";
import { useCartStore } from "@/lib/store/cartStore";

interface CartSummaryCompactProps {
  cart: Cart;
  branch: Branch | null;
}

/**
 * Blockers the customer resolves during checkout itself (choosing an address),
 * rather than in the cart. They are shown, but do not stop them proceeding.
 */
const CHECKOUT_STAGE_BLOCKERS = new Set(["address_required", "outside_delivery_area"]);

/**
 * Every figure here is the server's. The previous summary computed subtotal,
 * discount, a hardcoded ₦5.00 delivery fee and 7.5% tax *on top of* prices the
 * published terms said already included tax — and listed every promo code.
 */
export default function CartSummaryCompact({ cart, branch }: CartSummaryCompactProps) {
  const applyPromo = useCartStore((state) => state.applyPromo);
  const removePromo = useCartStore((state) => state.removePromo);
  const removeReward = useCartStore((state) => state.removeReward);
  const [rewardBusy, setRewardBusy] = useState(false);
  const reward = cart.loyalty_reward;

  const [promoCode, setPromoCode] = useState("");
  const [promoBusy, setPromoBusy] = useState(false);
  const [promoMessage, setPromoMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const { totals } = cart;
  const cartBlockers = cart.blockers.filter((b) => !CHECKOUT_STAGE_BLOCKERS.has(b.code) && b.code !== "cart_empty");
  const canProceed = cart.items.length > 0 && cartBlockers.length === 0;

  const handleApplyPromo = async () => {
    const code = promoCode.trim();
    if (!code) {
      setPromoMessage({ type: "error", text: "Enter a code" });
      return;
    }
    setPromoBusy(true);
    setPromoMessage(null);
    try {
      await applyPromo(code);
      setPromoCode("");
      setPromoMessage({ type: "success", text: "Code applied" });
    } catch (err) {
      setPromoMessage({ type: "error", text: err instanceof ApiError ? err.message : "That code couldn't be applied." });
    } finally {
      setPromoBusy(false);
    }
  };

  const handleRemovePromo = async () => {
    setPromoBusy(true);
    setPromoMessage(null);
    try {
      await removePromo();
    } catch (err) {
      setPromoMessage({ type: "error", text: err instanceof ApiError ? err.message : "Couldn't remove the code." });
    } finally {
      setPromoBusy(false);
    }
  };

  const minutes = cart.estimated_minutes ?? branch?.default_prep_minutes ?? null;

  return (
    <div className="sticky top-24 space-y-4">
      {/* Quick Info Cards */}
      {(branch?.free_delivery_threshold || minutes) && (
        <div className="grid grid-cols-2 gap-3">
          {branch?.free_delivery_threshold && (
            <div className="bg-white rounded-lg border p-3 text-center" style={{ borderColor: "var(--gray-mid)" }}>
              <Truck className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
              <p className="text-xs font-bold" style={{ color: "var(--black)" }}>Free Delivery</p>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>on orders over {branch.free_delivery_threshold.display}</p>
            </div>
          )}
          {minutes && (
            <div className="bg-white rounded-lg border p-3 text-center" style={{ borderColor: "var(--gray-mid)" }}>
              <Clock className="w-5 h-5 mx-auto mb-1" style={{ color: "var(--red)" }} />
              <p className="text-xs font-bold" style={{ color: "var(--black)" }}>About {minutes} mins</p>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                {cart.fulfilment_type === "pickup" ? "until ready" : "estimated"}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Main Summary */}
      <div className="bg-white rounded-xl border p-5" style={{ borderColor: "var(--gray-mid)" }}>
        <h2 className="font-black text-lg mb-4 flex items-center gap-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          <ShoppingBag className="w-5 h-5" style={{ color: "var(--red)" }} />
          Order Summary
        </h2>

        {/* Promo Code - Compact */}
        <div className="mb-4 pb-4" style={{ borderBottom: `1px solid var(--gray-mid)` }}>
          {cart.promo_code ? (
            <div className="flex items-center justify-between p-2 rounded-lg" style={{ background: "rgba(217,4,41,0.05)" }}>
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4" style={{ color: "var(--red)" }} />
                <div>
                  <p className="font-bold text-xs" style={{ color: "var(--black)" }}>{cart.promo_code}</p>
                  {totals.discount.amount > 0 && (
                    <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>−{totals.discount.display}</p>
                  )}
                </div>
              </div>
              <button
                onClick={handleRemovePromo}
                disabled={promoBusy}
                aria-label="Remove promo code"
                className="w-6 h-6 rounded-full flex items-center justify-center transition-all hover:opacity-80 disabled:opacity-50"
                style={{ background: "var(--red)" }}
              >
                {promoBusy ? <Loader2 className="w-3 h-3 text-white animate-spin" /> : <X className="w-3 h-3 text-white" />}
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
                  aria-label="Promo code"
                  maxLength={32}
                  className="flex-1 px-3 py-2 text-xs rounded-lg border outline-none transition-colors focus:border-red-500"
                  style={{ borderColor: "var(--gray-mid)" }}
                />
                <button
                  onClick={handleApplyPromo}
                  disabled={promoBusy}
                  className="px-3 py-2 rounded-lg text-xs font-bold transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ background: "var(--black)", color: "white" }}
                >
                  {promoBusy ? "..." : "Apply"}
                </button>
              </div>
            </div>
          )}

          {reward && (
            <div className="flex items-center justify-between p-2 rounded-lg mt-2" style={{ background: "rgba(217,4,41,0.05)" }}>
              <div className="flex items-center gap-2">
                <Gift className="w-4 h-4" style={{ color: "var(--red)" }} />
                <div>
                  <p className="font-bold text-xs" style={{ color: "var(--black)" }}>{reward.name} · {reward.points_cost} pts</p>
                  <p className="text-[10px]" style={{ color: reward.applied ? "var(--text-muted)" : "var(--red)" }}>
                    {reward.applied
                      ? reward.free_delivery ? "Free delivery" : `−${reward.discount.display}`
                      : reward.problem}
                  </p>
                </div>
              </div>
              <button
                onClick={async () => {
                  setRewardBusy(true);
                  try {
                    await removeReward();
                  } catch {
                    /* the reward stays shown; the customer can try again */
                  } finally {
                    setRewardBusy(false);
                  }
                }}
                disabled={rewardBusy}
                aria-label="Remove reward"
                className="w-6 h-6 rounded-full flex items-center justify-center transition-all hover:opacity-80 disabled:opacity-50"
                style={{ background: "var(--red)" }}
              >
                {rewardBusy ? <Loader2 className="w-3 h-3 text-white animate-spin" /> : <X className="w-3 h-3 text-white" />}
              </button>
            </div>
          )}

          {promoMessage && (
            <p
              role={promoMessage.type === "error" ? "alert" : "status"}
              className={`text-[10px] mt-2 flex items-center gap-1 ${promoMessage.type === "success" ? "text-green-600" : "text-red-600"}`}
            >
              {promoMessage.type === "success" ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
              {promoMessage.text}
            </p>
          )}
        </div>

        {/* Price Breakdown - Compact */}
        <div className="space-y-2 mb-4">
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Subtotal ({cart.item_count} {cart.item_count === 1 ? "item" : "items"})</span>
            <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.subtotal.display}</span>
          </div>

          {cart.promo_discount.amount > 0 && (
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--red)" }}>Discount</span>
              <span className="font-semibold" style={{ color: "var(--red)" }}>−{cart.promo_discount.display}</span>
            </div>
          )}

          {reward?.applied && reward.discount.amount > 0 && (
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--red)" }}>Reward</span>
              <span className="font-semibold" style={{ color: "var(--red)" }}>−{reward.discount.display}</span>
            </div>
          )}

          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>{cart.fulfilment_type === "pickup" ? "Pickup" : "Delivery"}</span>
            <span className="font-semibold" style={{ color: totals.delivery_fee.amount > 0 ? "var(--black)" : "var(--red)" }}>
              {totals.delivery_fee.amount > 0 ? totals.delivery_fee.display : "FREE"}
            </span>
          </div>

          {totals.service_charge.amount > 0 && (
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--text-muted)" }}>Service charge</span>
              <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.service_charge.display}</span>
            </div>
          )}

          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>{cart.prices_include_vat ? "VAT (included)" : "VAT"}</span>
            <span className="font-semibold" style={{ color: cart.prices_include_vat ? "var(--text-muted)" : "var(--black)" }}>
              {totals.vat.display}
            </span>
          </div>

          {totals.tip.amount > 0 && (
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--text-muted)" }}>Tip</span>
              <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.tip.display}</span>
            </div>
          )}

          <div className="h-px" style={{ background: "var(--gray-mid)" }} />

          <div className="flex justify-between items-center pt-1">
            <span className="font-bold text-sm" style={{ color: "var(--black)" }}>Total</span>
            <span className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
              {totals.grand_total.display}
            </span>
          </div>

          {(cart.vat_note || cart.delivery_note) && (
            <p className="text-[10px] pt-1" style={{ color: "var(--text-muted)" }}>
              {[cart.delivery_note, cart.vat_note].filter(Boolean).join(" ")}
            </p>
          )}
        </div>

        {cart.blockers.filter((b) => b.code !== "cart_empty").length > 0 && (
          <ul className="mb-4 space-y-1">
            {cart.blockers
              .filter((b) => b.code !== "cart_empty")
              .map((blocker) => (
                <li
                  key={blocker.code}
                  className="flex items-start gap-1.5 text-xs"
                  style={{ color: CHECKOUT_STAGE_BLOCKERS.has(blocker.code) ? "var(--text-muted)" : "var(--red)" }}
                >
                  <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  {blocker.detail}
                </li>
              ))}
          </ul>
        )}

        {/* Actions */}
        <div className="space-y-2">
          {canProceed ? (
            <Link
              href="/checkout"
              className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-[1.02]"
              style={{ background: "var(--red)", boxShadow: "0 4px 14px rgba(217,4,41,0.3)" }}
            >
              Proceed to Checkout
            </Link>
          ) : (
            <button
              disabled
              className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-full text-sm font-bold text-white opacity-50 cursor-not-allowed"
              style={{ background: "var(--red)" }}
            >
              Proceed to Checkout
            </button>
          )}

          <Link
            href="/menu"
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
