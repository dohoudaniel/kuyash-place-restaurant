"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { AlertCircle, Loader2 } from "lucide-react";
import { ApiError, newIdempotencyKey } from "@/lib/api/client";
import { mediaUrl } from "@/lib/api/media";
import { initialisePayment, placeOrder } from "@/lib/api/orders";
import type { Branch, Cart } from "@/lib/api/types";
import { useCartStore } from "@/lib/store/cartStore";
import type { DeliveryData } from "./DeliveryStep";
import type { PaymentData } from "./PaymentStep";

interface ReviewStepProps {
  cart: Cart;
  branch: Branch | null;
  deliveryData: DeliveryData;
  paymentData: PaymentData;
  onBack: () => void;
  /** Tells the page an order is being placed, so an emptied cart does not redirect away. */
  onPlacingChange: (placing: boolean) => void;
}

const PAYMENT_LABELS = { card: "Pay Online", transfer: "Bank Transfer", cash: "Cash" } as const;

/**
 * The last look before the order is placed.
 *
 * Everything shown is the server's cart. The previous review recomputed a
 * subtotal, a hardcoded ₦5.00 delivery fee and 7.5% tax in the browser, then
 * "placed" the order by writing it to localStorage.
 */
export default function ReviewStep({ cart, branch, deliveryData, paymentData, onBack, onPlacingChange }: ReviewStepProps) {
  const router = useRouter();
  const refreshCart = useCartStore((state) => state.refresh);
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // One key per attempt. Kept across a retry after a network failure, so a
  // double-tap or a flaky connection can never place the same order twice.
  const attemptKey = useRef<string | null>(null);

  const { totals } = cart;
  const blockers = cart.blockers.filter((b) => b.code !== "cart_empty");

  const handleConfirm = async () => {
    attemptKey.current ??= newIdempotencyKey();
    setPlacing(true);
    setError(null);
    onPlacingChange(true);

    try {
      const order = await placeOrder(
        {
          payment_method: paymentData.method,
          expected_total: totals.grand_total.amount,
          customer_note: deliveryData.customerNote,
          guest: deliveryData.guest ?? undefined,
        },
        attemptKey.current
      );
      attemptKey.current = null;

      if (paymentData.method === "card") {
        try {
          const payment = await initialisePayment(order.reference, paymentData.saveCard);
          window.location.assign(payment.authorization_url);
          return;
        } catch {
          // The order exists; paying can be retried from its page.
          void refreshCart();
          router.push(`/orders/${encodeURIComponent(order.reference)}?payment=retry`);
          return;
        }
      }

      void refreshCart();
      router.push(`/orders/${encodeURIComponent(order.reference)}?placed=1`);
    } catch (err) {
      setPlacing(false);
      onPlacingChange(false);
      if (err instanceof ApiError && err.isNetworkError) {
        setError("We couldn't reach the restaurant. Please try again — you won't be charged twice.");
        return;
      }
      attemptKey.current = null;
      await refreshCart();
      if (err instanceof ApiError && err.code === "price_changed") {
        setError("Prices changed while you were checking out. Please check the new total and confirm again.");
      } else {
        setError(err instanceof ApiError ? err.message : "We couldn't place your order. Please try again.");
      }
    }
  };

  const address = deliveryData.address;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Review Your Order
        </h2>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Left Column - Order Items */}
          <div>
            <h3 className="font-bold text-sm uppercase tracking-wide mb-4" style={{ color: "var(--black)" }}>
              Order Items ({cart.item_count})
            </h3>

            <div className="space-y-3 mb-6">
              {cart.items.map((line) => {
                const imageSrc = mediaUrl(line.menu_item.image_url);
                const details = [line.variant_name, ...line.modifiers.map((m) => m.name)].filter(Boolean).join(" · ");
                return (
                  <div key={line.id} className="flex gap-3 p-3 rounded-lg" style={{ background: "var(--off-white)" }}>
                    <div className="relative w-16 h-16 rounded-lg overflow-hidden shrink-0" style={{ background: "var(--cream)" }}>
                      {imageSrc ? (
                        <Image src={imageSrc} alt={line.menu_item.name} fill className="object-cover" sizes="64px" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xl">🍔</div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate" style={{ color: "var(--black)" }}>
                        {line.menu_item.name}
                      </p>
                      {details && (
                        <p className="text-xs mt-0.5 truncate" style={{ color: "var(--text-muted)" }}>{details}</p>
                      )}
                      <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                        Qty: {line.quantity}
                      </p>
                    </div>

                    <div className="font-bold text-sm" style={{ color: "var(--red)" }}>
                      {line.line_subtotal.display}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Price Summary */}
            <div className="space-y-2 pt-4" style={{ borderTop: `1px solid var(--gray-mid)` }}>
              <div className="flex justify-between text-sm">
                <span style={{ color: "var(--text-muted)" }}>Subtotal</span>
                <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.subtotal.display}</span>
              </div>
              {totals.discount.amount > 0 && (
                <div className="flex justify-between text-sm">
                  <span style={{ color: "var(--red)" }}>Discount{cart.promo_code ? ` (${cart.promo_code})` : ""}</span>
                  <span className="font-semibold" style={{ color: "var(--red)" }}>−{totals.discount.display}</span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span style={{ color: "var(--text-muted)" }}>{cart.fulfilment_type === "pickup" ? "Pickup" : "Delivery Fee"}</span>
                <span className="font-semibold" style={{ color: "var(--black)" }}>
                  {totals.delivery_fee.amount > 0 ? totals.delivery_fee.display : <span style={{ color: "var(--red)" }}>Free</span>}
                </span>
              </div>
              {totals.service_charge.amount > 0 && (
                <div className="flex justify-between text-sm">
                  <span style={{ color: "var(--text-muted)" }}>Service Charge</span>
                  <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.service_charge.display}</span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span style={{ color: "var(--text-muted)" }}>{cart.prices_include_vat ? "VAT (included)" : "VAT"}</span>
                <span className="font-semibold" style={{ color: cart.prices_include_vat ? "var(--text-muted)" : "var(--black)" }}>{totals.vat.display}</span>
              </div>
              {totals.tip.amount > 0 && (
                <div className="flex justify-between text-sm">
                  <span style={{ color: "var(--text-muted)" }}>Tip</span>
                  <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.tip.display}</span>
                </div>
              )}
              <div className="flex justify-between pt-2" style={{ borderTop: `1px solid var(--gray-mid)` }}>
                <span className="font-bold" style={{ color: "var(--black)" }}>Total</span>
                <span className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                  {totals.grand_total.display}
                </span>
              </div>
              {cart.vat_note && (
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{cart.vat_note}</p>
              )}
            </div>
          </div>

          {/* Right Column - Delivery & Payment Info */}
          <div className="space-y-6">
            {/* Delivery Information */}
            <div>
              <h3 className="font-bold text-sm uppercase tracking-wide mb-3" style={{ color: "var(--black)" }}>
                {deliveryData.fulfilment === "pickup" ? "Pickup" : "Delivery Address"}
              </h3>
              <div className="p-4 rounded-lg space-y-2" style={{ background: "var(--off-white)" }}>
                {deliveryData.fulfilment === "delivery" && address ? (
                  <>
                    <p className="font-semibold text-sm" style={{ color: "var(--black)" }}>{address.recipient_name}</p>
                    <p className="text-sm" style={{ color: "var(--text-muted)" }}>{address.phone}</p>
                    <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                      {[address.street, address.area].filter(Boolean).join(", ")}
                    </p>
                    <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                      {address.city}, {address.state}
                    </p>
                    {address.landmark && (
                      <p className="text-sm" style={{ color: "var(--text-muted)" }}>Near {address.landmark}</p>
                    )}
                  </>
                ) : (
                  <>
                    <p className="font-semibold text-sm" style={{ color: "var(--black)" }}>{branch?.name ?? "Kuyash Place"}</p>
                    <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                      {[branch?.address_line, branch?.city].filter(Boolean).join(", ")}
                    </p>
                  </>
                )}
                {deliveryData.guest && (
                  <p className="text-xs pt-2" style={{ borderTop: `1px solid var(--gray-mid)`, color: "var(--text-muted)" }}>
                    {deliveryData.guest.full_name} · {deliveryData.guest.email} · {deliveryData.guest.phone}
                  </p>
                )}
                {deliveryData.customerNote && (
                  <p className="text-xs mt-2 pt-2" style={{ borderTop: `1px solid var(--gray-mid)`, color: "var(--text-muted)" }}>
                    Note: {deliveryData.customerNote}
                  </p>
                )}
              </div>
            </div>

            {/* Payment Method */}
            <div>
              <h3 className="font-bold text-sm uppercase tracking-wide mb-3" style={{ color: "var(--black)" }}>
                Payment Method
              </h3>
              <div className="p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
                <p className="font-semibold text-sm" style={{ color: "var(--black)" }}>
                  {paymentData.method === "cash" && deliveryData.fulfilment === "pickup" ? "Pay at Pickup" : paymentData.method === "cash" ? "Cash on Delivery" : PAYMENT_LABELS[paymentData.method]}
                </p>
                {paymentData.method === "card" && (
                  <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                    You&apos;ll pay on our payment partner&apos;s secure page next.
                  </p>
                )}
                {paymentData.method === "transfer" && (
                  <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                    Account details and your reference are shown once the order is placed.
                  </p>
                )}
              </div>
            </div>

            {/* Estimated Time */}
            {cart.estimated_minutes && (
              <div>
                <h3 className="font-bold text-sm uppercase tracking-wide mb-3" style={{ color: "var(--black)" }}>
                  {deliveryData.fulfilment === "pickup" ? "Ready In" : "Estimated Delivery"}
                </h3>
                <div className="p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
                  <p className="font-semibold text-sm" style={{ color: "var(--red)" }}>
                    About {cart.estimated_minutes} minutes
                  </p>
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    {cart.delivery_note || "Your order will arrive fresh and hot!"}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {blockers.length > 0 && (
          <ul className="mt-6 space-y-1">
            {blockers.map((blocker) => (
              <li key={blocker.code} className="flex items-start gap-2 text-sm font-semibold" style={{ color: "var(--red)" }}>
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                {blocker.detail}
              </li>
            ))}
          </ul>
        )}

        {error && (
          <p role="alert" className="mt-6 flex items-start gap-2 text-sm font-semibold" style={{ color: "var(--red)" }}>
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            {error}
          </p>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4 mt-8">
          <button
            type="button"
            onClick={onBack}
            disabled={placing}
            className="flex-1 px-6 py-3.5 rounded-full text-sm font-bold transition-all duration-200 hover:bg-gray-100 disabled:opacity-50"
            style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
          >
            Back
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={placing || !cart.can_checkout}
            className="flex-1 px-6 py-3.5 rounded-full text-sm font-bold text-white flex items-center justify-center gap-2 transition-all duration-200 hover:opacity-90 hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
            style={{ background: "var(--red)", boxShadow: "0 8px 28px rgba(217,4,41,0.35)" }}
          >
            {placing && <Loader2 className="w-4 h-4 animate-spin" />}
            {placing
              ? paymentData.method === "card" ? "Opening payment..." : "Placing order..."
              : paymentData.method === "card" ? `Place Order & Pay ${totals.grand_total.display}` : "Confirm & Place Order"}
          </button>
        </div>
      </div>
    </div>
  );
}
