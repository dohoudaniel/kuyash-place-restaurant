"use client";

import { useState } from "react";
import { CreditCard, Wallet, Banknote } from "lucide-react";

interface PaymentStepProps {
  onNext: (data: PaymentData) => void;
  onBack: () => void;
}

export interface PaymentData {
  method: "card" | "transfer" | "cash";
  cardNumber?: string;
  cardName?: string;
  cardExpiry?: string;
  cardCvv?: string;
}

export default function PaymentStep({ onNext, onBack }: PaymentStepProps) {
  const [paymentMethod, setPaymentMethod] = useState<"card" | "transfer" | "cash">("card");
  const [cardData, setCardData] = useState({
    cardNumber: "",
    cardName: "",
    cardExpiry: "",
    cardCvv: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onNext({
      method: paymentMethod,
      ...cardData,
    });
  };

  const paymentMethods = [
    { id: "card", label: "Credit/Debit Card", icon: CreditCard },
    { id: "transfer", label: "Bank Transfer", icon: Wallet },
    { id: "cash", label: "Cash on Delivery", icon: Banknote },
  ];

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Payment Method
        </h2>

        {/* Payment Method Selection */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          {paymentMethods.map((method) => {
            const Icon = method.icon;
            const isSelected = paymentMethod === method.id;

            return (
              <button
                key={method.id}
                type="button"
                onClick={() => setPaymentMethod(method.id as typeof paymentMethod)}
                className="p-4 rounded-lg border-2 transition-all hover:scale-105 active:scale-95"
                style={{
                  borderColor: isSelected ? "var(--red)" : "var(--gray-mid)",
                  background: isSelected ? "rgba(217,4,41,0.05)" : "white",
                }}
              >
                <Icon className="w-6 h-6 mx-auto mb-2" style={{ color: isSelected ? "var(--red)" : "var(--text-muted)" }} />
                <p className="text-sm font-semibold" style={{ color: isSelected ? "var(--red)" : "var(--black)" }}>
                  {method.label}
                </p>
              </button>
            );
          })}
        </div>

        {/* Card Details Form */}
        {paymentMethod === "card" && (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
                Card Number
              </label>
              <input
                type="text"
                required
                value={cardData.cardNumber}
                onChange={(e) => setCardData({ ...cardData, cardNumber: e.target.value })}
                placeholder="1234 5678 9012 3456"
                maxLength={19}
                className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>

            <div>
              <label className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
                Cardholder Name
              </label>
              <input
                type="text"
                required
                value={cardData.cardName}
                onChange={(e) => setCardData({ ...cardData, cardName: e.target.value })}
                placeholder="John Doe"
                className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
                  Expiry Date
                </label>
                <input
                  type="text"
                  required
                  value={cardData.cardExpiry}
                  onChange={(e) => setCardData({ ...cardData, cardExpiry: e.target.value })}
                  placeholder="MM/YY"
                  maxLength={5}
                  className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
                  style={{ borderColor: "var(--gray-mid)" }}
                />
              </div>

              <div>
                <label className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
                  CVV
                </label>
                <input
                  type="text"
                  required
                  value={cardData.cardCvv}
                  onChange={(e) => setCardData({ ...cardData, cardCvv: e.target.value })}
                  placeholder="123"
                  maxLength={4}
                  className="w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500"
                  style={{ borderColor: "var(--gray-mid)" }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Bank Transfer Info */}
        {paymentMethod === "transfer" && (
          <div className="p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
            <p className="text-sm mb-2" style={{ color: "var(--text-muted)" }}>
              You will receive bank transfer details after placing your order.
            </p>
            <p className="text-xs font-semibold" style={{ color: "var(--black)" }}>
              Please complete payment within 24 hours to confirm your order.
            </p>
          </div>
        )}

        {/* Cash on Delivery Info */}
        {paymentMethod === "cash" && (
          <div className="p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
            <p className="text-sm mb-2" style={{ color: "var(--text-muted)" }}>
              Pay with cash when your order is delivered.
            </p>
            <p className="text-xs font-semibold" style={{ color: "var(--black)" }}>
              Please have the exact amount ready for the delivery rider.
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4 mt-6">
          <button
            type="button"
            onClick={onBack}
            className="flex-1 px-6 py-3.5 rounded-full text-sm font-bold transition-all duration-200 hover:bg-gray-100"
            style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
          >
            Back
          </button>
          <button
            type="submit"
            className="flex-1 px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-[1.02] active:scale-95"
            style={{ background: "var(--red)" }}
          >
            Review Order
          </button>
        </div>
      </div>
    </form>
  );
}
