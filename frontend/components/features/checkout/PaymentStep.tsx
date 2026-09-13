"use client";

import { useState } from "react";
import { CreditCard, Wallet, Banknote, ShieldCheck } from "lucide-react";

interface PaymentStepProps {
  onNext: (data: PaymentData) => void;
  onBack: () => void;
}

/**
 * The customer's choice of how to pay — and nothing else.
 *
 * Card details are never collected here. Paying online sends the customer to
 * the payment provider's hosted page after the order is placed, so card data
 * never touches this app or the Kuyash Place servers (PCI-DSS SAQ A; see
 * backend/docs/PAYMENTS.md §1).
 */
export interface PaymentData {
  method: "card" | "transfer" | "cash";
}

export default function PaymentStep({ onNext, onBack }: PaymentStepProps) {
  const [paymentMethod, setPaymentMethod] = useState<PaymentData["method"]>("card");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onNext({ method: paymentMethod });
  };

  const paymentMethods = [
    { id: "card", label: "Pay Online", icon: CreditCard },
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
                onClick={() => setPaymentMethod(method.id as PaymentData["method"])}
                aria-pressed={isSelected}
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

        {/* Online Payment Info */}
        {paymentMethod === "card" && (
          <div className="p-4 rounded-lg flex gap-3" style={{ background: "var(--off-white)" }}>
            <ShieldCheck className="w-5 h-5 shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
            <div>
              <p className="text-sm mb-2" style={{ color: "var(--text-muted)" }}>
                After you place your order, you&apos;ll pay by card, bank or USSD on our payment
                partner&apos;s secure page, then come straight back here.
              </p>
              <p className="text-xs font-semibold" style={{ color: "var(--black)" }}>
                Kuyash Place never sees or stores your card details.
              </p>
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
