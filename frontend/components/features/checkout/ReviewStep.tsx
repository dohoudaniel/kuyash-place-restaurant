"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";
import { useCartStore } from "@/lib/store/cartStore";
import { useOrderHistoryStore } from "@/lib/store/orderHistoryStore";
import { usePromoStore } from "@/lib/store/promoStore";
import { IMAGES, type ImageKey } from "@/lib/assets/images";
import type { DeliveryData } from "./DeliveryStep";
import type { PaymentData } from "./PaymentStep";

interface ReviewStepProps {
  deliveryData: DeliveryData;
  paymentData: PaymentData;
  onBack: () => void;
  onConfirm: () => void;
}

export default function ReviewStep({ deliveryData, paymentData, onBack, onConfirm }: ReviewStepProps) {
  const router = useRouter();
  const { items, getTotalPrice, clearCart } = useCartStore();
  const { addOrder } = useOrderHistoryStore();
  const { calculateDiscount, appliedPromo, removePromo } = usePromoStore();

  const subtotal = getTotalPrice();
  const discount = calculateDiscount(subtotal);
  const deliveryFee = appliedPromo?.type === "freeDelivery" ? 0 : 5.00;
  const tax = (subtotal - discount) * 0.075;
  const total = subtotal - discount + deliveryFee + tax;

  const getPaymentMethodLabel = () => {
    switch (paymentData.method) {
      case "card":
        return "Credit/Debit Card";
      case "transfer":
        return "Bank Transfer";
      case "cash":
        return "Cash on Delivery";
      default:
        return "";
    }
  };

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
              Order Items ({items.length})
            </h3>

            <div className="space-y-3 mb-6">
              {items.map((item) => {
                const imageSrc = item.imageKey ? IMAGES.menu[item.imageKey as ImageKey] : null;

                return (
                  <div key={item.id} className="flex gap-3 p-3 rounded-lg" style={{ background: "var(--off-white)" }}>
                    <div className="relative w-16 h-16 rounded-lg overflow-hidden shrink-0" style={{ background: "var(--cream)" }}>
                      {imageSrc ? (
                        <Image src={imageSrc} alt={item.name} fill className="object-cover" sizes="64px" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xl">🍔</div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate" style={{ color: "var(--black)" }}>
                        {item.name}
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                        Qty: {item.quantity}
                      </p>
                    </div>

                    <div className="font-bold text-sm" style={{ color: "var(--red)" }}>
                      ₦{(item.price * item.quantity).toFixed(2)}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Price Summary */}
            <div className="space-y-2 pt-4" style={{ borderTop: `1px solid var(--gray-mid)` }}>
              <div className="flex justify-between text-sm">
                <span style={{ color: "var(--text-muted)" }}>Subtotal</span>
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
              <div className="flex justify-between pt-2" style={{ borderTop: `1px solid var(--gray-mid)` }}>
                <span className="font-bold" style={{ color: "var(--black)" }}>Total</span>
                <span className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                  ₦{total.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          {/* Right Column - Delivery & Payment Info */}
          <div className="space-y-6">
            {/* Delivery Information */}
            <div>
              <h3 className="font-bold text-sm uppercase tracking-wide mb-3" style={{ color: "var(--black)" }}>
                Delivery Address
              </h3>
              <div className="p-4 rounded-lg space-y-2" style={{ background: "var(--off-white)" }}>
                <p className="font-semibold text-sm" style={{ color: "var(--black)" }}>
                  {deliveryData.fullName}
                </p>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  {deliveryData.phone}
                </p>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  {deliveryData.address}
                </p>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  {deliveryData.city}, {deliveryData.state} {deliveryData.zipCode}
                </p>
                {deliveryData.deliveryNotes && (
                  <p className="text-xs mt-2 pt-2" style={{ borderTop: `1px solid var(--gray-mid)`, color: "var(--text-muted)" }}>
                    Note: {deliveryData.deliveryNotes}
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
                  {getPaymentMethodLabel()}
                </p>
                {paymentData.method === "card" && paymentData.cardNumber && (
                  <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                    •••• {paymentData.cardNumber.slice(-4)}
                  </p>
                )}
              </div>
            </div>

            {/* Estimated Delivery */}
            <div>
              <h3 className="font-bold text-sm uppercase tracking-wide mb-3" style={{ color: "var(--black)" }}>
                Estimated Delivery
              </h3>
              <div className="p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
                <p className="font-semibold text-sm" style={{ color: "var(--red)" }}>
                  30-45 minutes
                </p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  Your order will arrive fresh and hot!
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 mt-8">
          <button
            type="button"
            onClick={onBack}
            className="flex-1 px-6 py-3.5 rounded-full text-sm font-bold transition-all duration-200 hover:bg-gray-100"
            style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
          >
            Back
          </button>
          <button
            type="button"
            onClick={() => {
              const orderId = `KYS-${Date.now().toString(36).toUpperCase()}`;

              addOrder({
                orderId,
                status: "confirmed",
                orderDate: new Date().toISOString(),
                items: items.map(item => ({
                  id: item.id,
                  name: item.name,
                  description: item.description,
                  price: item.price,
                  quantity: item.quantity,
                  imageKey: item.imageKey,
                })),
                deliveryAddress: deliveryData,
                paymentMethod: paymentData.method,
                pricing: {
                  subtotal,
                  deliveryFee,
                  tax,
                  discount,
                  tip: 0,
                  total,
                },
                promoCode: appliedPromo?.code,
                deliveryOption: "standard",
              });

              clearCart();
              removePromo();
              router.push(`/orders/${orderId}`);
            }}
            className="flex-1 px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-[1.02] active:scale-95"
            style={{ background: "var(--red)", boxShadow: "0 8px 28px rgba(217,4,41,0.35)" }}
          >
            Confirm & Place Order
          </button>
        </div>
      </div>
    </div>
  );
}
