"use client";

import { MapPin, CreditCard, Wallet, Banknote } from "lucide-react";

interface OrderSummaryProps {
  deliveryAddress: {
    fullName: string;
    phone: string;
    address: string;
    city: string;
    state: string;
    zipCode: string;
    deliveryNotes?: string;
  };
  paymentMethod: "card" | "transfer" | "cash";
  pricing: {
    subtotal: number;
    deliveryFee: number;
    tax: number;
    total: number;
  };
}

export default function OrderSummary({ deliveryAddress, paymentMethod, pricing }: OrderSummaryProps) {
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

  const PaymentIcon = paymentIcons[paymentMethod];

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Order Summary
      </h2>

      {/* Delivery Address */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <MapPin className="w-5 h-5" style={{ color: "var(--red)" }} />
          <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>Delivery Address</h3>
        </div>
        <div className="pl-7 space-y-1">
          <p className="font-semibold text-sm" style={{ color: "var(--black)" }}>{deliveryAddress.fullName}</p>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>{deliveryAddress.phone}</p>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {deliveryAddress.address}, {deliveryAddress.city}, {deliveryAddress.state} {deliveryAddress.zipCode}
          </p>
          {deliveryAddress.deliveryNotes && (
            <p className="text-xs italic mt-2" style={{ color: "var(--text-muted)" }}>
              Note: {deliveryAddress.deliveryNotes}
            </p>
          )}
        </div>
      </div>

      {/* Payment Method */}
      <div className="mb-6 pb-6 border-b" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-center gap-2 mb-3">
          <PaymentIcon className="w-5 h-5" style={{ color: "var(--red)" }} />
          <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>Payment Method</h3>
        </div>
        <p className="pl-7 text-sm" style={{ color: "var(--text-muted)" }}>
          {paymentLabels[paymentMethod]}
        </p>
      </div>

      {/* Price Breakdown */}
      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>Subtotal</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>₦{pricing.subtotal.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>Delivery Fee</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>₦{pricing.deliveryFee.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>Tax (7.5%)</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>₦{pricing.tax.toFixed(2)}</span>
        </div>
        <div className="pt-3 border-t" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex justify-between items-center">
            <span className="font-bold text-base" style={{ color: "var(--black)" }}>Total</span>
            <span className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
              ₦{pricing.total.toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
