"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";
import { MapPin, CreditCard, Wallet, Banknote, Clock, Package, Gift } from "lucide-react";
import { useCartStore } from "@/lib/store/cartStore";
import { useOrderHistoryStore } from "@/lib/store/orderHistoryStore";
import { usePromoStore } from "@/lib/store/promoStore";
import type { DeliveryData } from "./DeliveryStep";
import type { PaymentData } from "./PaymentStep";

interface ReviewStepCompactProps {
  deliveryData: DeliveryData;
  paymentData: PaymentData;
  deliveryOption: "standard" | "express" | "scheduled";
  scheduledTime: string;
  tip: number;
  onBack: () => void;
  onConfirm: () => void;
}

export default function ReviewStepCompact({
  deliveryData,
  paymentData,
  deliveryOption,
  scheduledTime,
  tip,
  onBack,
}: ReviewStepCompactProps) {
  const router = useRouter();
  const { items, getTotalPrice, clearCart } = useCartStore();
  const { addOrder } = useOrderHistoryStore();
  const { calculateDiscount, appliedPromo, removePromo } = usePromoStore();

  const subtotal = getTotalPrice();
  const discount = calculateDiscount(subtotal);
  const deliveryFee =
    appliedPromo?.type === "freeDelivery" ? 0 : deliveryOption === "express" ? 10.0 : 5.0;
  const tax = (subtotal - discount) * 0.075;
  const total = subtotal - discount + deliveryFee + tax + tip;

  const paymentIcons = {
    card: CreditCard,
    transfer: Wallet,
    cash: Banknote,
  };

  const paymentLabels = {
    card: "Credit/Debit Card",
    transfer: "Bank Transfer",
    cash: "Cash on Delivery",
  };

  const deliveryLabels = {
    standard: "Standard Delivery (30-45 min)",
    express: "Express Delivery (15-20 min)",
    scheduled: `Scheduled Delivery`,
  };

  const PaymentIcon = paymentIcons[paymentData.method];

  const handleConfirmOrder = () => {
    const orderId = `KYS-${Date.now().toString(36).toUpperCase()}`;

    addOrder({
      orderId,
      status: "confirmed",
      orderDate: new Date().toISOString(),
      items: items.map((item) => ({
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
        tip,
        total,
      },
      promoCode: appliedPromo?.code,
      deliveryOption,
      scheduledTime,
    });

    clearCart();
    removePromo();
    router.push(`/orders/${orderId}`);
  };

  return (
    <div className="space-y-6">
      <h2 className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Review Your Order
      </h2>

      {/* 2-Column Layout for Info Cards */}
      <div className="grid sm:grid-cols-2 gap-4">
        {/* Delivery Info */}
        <div className="p-4 rounded-xl" style={{ background: "rgba(217,4,41,0.02)", border: "1px solid var(--gray-mid)" }}>
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="w-4 h-4" style={{ color: "var(--red)" }} />
            <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>Delivery Address</h3>
          </div>
          <div className="space-y-1 text-xs">
            <p className="font-semibold" style={{ color: "var(--black)" }}>{deliveryData.fullName}</p>
            <p style={{ color: "var(--text-muted)" }}>{deliveryData.phone}</p>
            <p style={{ color: "var(--text-muted)" }}>
              {deliveryData.address}, {deliveryData.city}
            </p>
            <p style={{ color: "var(--text-muted)" }}>
              {deliveryData.state} {deliveryData.zipCode}
            </p>
            {deliveryData.deliveryNotes && (
              <p className="text-[10px] italic mt-2 pt-2" style={{ borderTop: "1px solid var(--gray-mid)", color: "var(--text-muted)" }}>
                "{deliveryData.deliveryNotes}"
              </p>
            )}
          </div>
        </div>

        {/* Payment Info */}
        <div className="p-4 rounded-xl" style={{ background: "rgba(217,4,41,0.02)", border: "1px solid var(--gray-mid)" }}>
          <div className="flex items-center gap-2 mb-3">
            <PaymentIcon className="w-4 h-4" style={{ color: "var(--red)" }} />
            <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>Payment Method</h3>
          </div>
          <div className="space-y-1 text-xs">
            <p className="font-semibold" style={{ color: "var(--black)" }}>
              {paymentLabels[paymentData.method]}
            </p>
            {paymentData.method === "card" && paymentData.cardNumber && (
              <p style={{ color: "var(--text-muted)" }}>•••• {paymentData.cardNumber.slice(-4)}</p>
            )}
          </div>
        </div>

        {/* Delivery Option */}
        <div className="p-4 rounded-xl" style={{ background: "rgba(217,4,41,0.02)", border: "1px solid var(--gray-mid)" }}>
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4" style={{ color: "var(--red)" }} />
            <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>Delivery Time</h3>
          </div>
          <div className="space-y-1 text-xs">
            <p className="font-semibold" style={{ color: "var(--black)" }}>
              {deliveryLabels[deliveryOption]}
            </p>
            {deliveryOption === "scheduled" && scheduledTime && (
              <p style={{ color: "var(--text-muted)" }}>
                {new Date(scheduledTime).toLocaleString()}
              </p>
            )}
          </div>
        </div>

        {/* Tip Info */}
        {tip > 0 && (
          <div className="p-4 rounded-xl" style={{ background: "rgba(217,4,41,0.02)", border: "1px solid var(--gray-mid)" }}>
            <div className="flex items-center gap-2 mb-3">
              <Gift className="w-4 h-4" style={{ color: "var(--red)" }} />
              <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>Tip</h3>
            </div>
            <div className="space-y-1 text-xs">
              <p className="font-semibold" style={{ color: "var(--red)" }}>₦{tip.toFixed(2)}</p>
              <p style={{ color: "var(--text-muted)" }}>Thank you for your generosity! 💝</p>
            </div>
          </div>
        )}
      </div>

      {/* Order Items - Compact Horizontal Cards */}
      <div className="p-4 rounded-xl" style={{ background: "white", border: "1px solid var(--gray-mid)" }}>
        <div className="flex items-center gap-2 mb-4">
          <Package className="w-4 h-4" style={{ color: "var(--red)" }} />
          <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>
            Order Items ({items.length})
          </h3>
        </div>

        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-3 p-2 rounded-lg"
              style={{ background: "var(--off-white)" }}
            >
              <div className="shrink-0 w-12 h-12 rounded-lg overflow-hidden relative" style={{ background: "var(--cream)" }}>
                {item.imageKey ? (
                  <Image
                    src={`/assets/menu/${item.imageKey}.png`}
                    alt={item.name}
                    fill
                    className="object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-lg">🍽️</div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold text-xs truncate" style={{ color: "var(--black)" }}>
                  {item.name}
                </h4>
                <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                  Qty: {item.quantity} × ₦{item.price.toFixed(2)}
                </p>
              </div>
              <p className="font-bold text-sm shrink-0" style={{ color: "var(--red)" }}>
                ₦{(item.price * item.quantity).toFixed(2)}
              </p>
            </div>
          ))}
        </div>

        {/* Price Summary - Inline */}
        <div className="mt-4 pt-4 space-y-2" style={{ borderTop: "1px solid var(--gray-mid)" }}>
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Subtotal</span>
            <span className="font-semibold" style={{ color: "var(--black)" }}>₦{subtotal.toFixed(2)}</span>
          </div>
          {discount > 0 && (
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--red)" }}>Discount ({appliedPromo?.code})</span>
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
          <div className="flex justify-between items-center pt-2" style={{ borderTop: "1px solid var(--gray-mid)" }}>
            <span className="font-bold text-sm" style={{ color: "var(--black)" }}>Total</span>
            <span className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
              ₦{total.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="flex-1 px-6 py-3 rounded-full text-sm font-bold transition-all hover:bg-gray-50"
          style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
        >
          Back
        </button>
        <button
          type="button"
          onClick={handleConfirmOrder}
          className="flex-1 px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90 hover:scale-[1.02]"
          style={{ background: "var(--red)", boxShadow: "0 4px 20px rgba(217,4,41,0.4)" }}
        >
          Confirm & Place Order
        </button>
      </div>
    </div>
  );
}
