"use client";

import { useState } from "react";
import { CreditCard, Wallet, Banknote, ShieldCheck, Check } from "lucide-react";
import type { Branch } from "@/lib/api/types";

interface PaymentStepProps {
  initial: PaymentData | null;
  fulfilment: "delivery" | "pickup";
  branch: Branch | null;
  isSignedIn: boolean;
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
  /** Consent to keep the card for next time. Signed-in customers only. */
  saveCard: boolean;
}

export default function PaymentStep({ initial, fulfilment, branch, isSignedIn, onNext, onBack }: PaymentStepProps) {
  const bank = branch?.bank_transfer ?? null;
  const [paymentMethod, setPaymentMethod] = useState<PaymentData["method"]>(
    initial?.method === "transfer" && !bank ? "card" : initial?.method ?? "card"
  );
  const [saveCard, setSaveCard] = useState(initial?.saveCard ?? false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onNext({ method: paymentMethod, saveCard: isSignedIn && paymentMethod === "card" && saveCard });
  };

  // Bank transfer only appears once the restaurant has entered an account to pay into.
  const paymentMethods = [
    { id: "card", label: "Pay Online", icon: CreditCard },
    ...(bank ? [{ id: "transfer", label: "Bank Transfer", icon: Wallet }] : []),
    { id: "cash", label: fulfilment === "pickup" ? "Pay at Pickup" : "Cash on Delivery", icon: Banknote },
  ];

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Payment Method
        </h2>

        {/* Payment Method Selection */}
        <div
          className={`grid grid-cols-1 ${paymentMethods.length === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2"} gap-4 mb-6`}
          role="radiogroup"
          aria-label="Payment method"
        >
          {paymentMethods.map((method) => {
            const Icon = method.icon;
            const isSelected = paymentMethod === method.id;

            return (
              <button
                key={method.id}
                type="button"
                role="radio"
                onClick={() => setPaymentMethod(method.id as PaymentData["method"])}
                aria-checked={isSelected}
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
          <div className="space-y-3">
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

            {isSignedIn && (
              <label htmlFor="save-card" className="flex items-start gap-3 cursor-pointer">
                <input
                  id="save-card"
                  type="checkbox"
                  checked={saveCard}
                  onChange={(e) => setSaveCard(e.target.checked)}
                  className="peer sr-only"
                />
                <span
                  aria-hidden="true"
                  className="w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all peer-focus-visible:ring-2 peer-focus-visible:ring-offset-2"
                  style={{ borderColor: saveCard ? "var(--red)" : "var(--gray-mid)", background: saveCard ? "var(--red)" : "white" }}
                >
                  {saveCard && <Check className="w-3 h-3 text-white" />}
                </span>
                <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                  Keep this card for faster checkout next time
                </span>
              </label>
            )}
          </div>
        )}

        {/* Bank Transfer Info */}
        {paymentMethod === "transfer" && bank && (
          <div className="p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
            <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>
              Transfer the order total to this account, using your order reference as the narration.
              We&apos;ll confirm your order once the payment arrives.
            </p>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              <dt style={{ color: "var(--text-muted)" }}>Bank</dt>
              <dd className="font-semibold" style={{ color: "var(--black)" }}>{bank.bank_name}</dd>
              <dt style={{ color: "var(--text-muted)" }}>Account name</dt>
              <dd className="font-semibold" style={{ color: "var(--black)" }}>{bank.account_name}</dd>
              <dt style={{ color: "var(--text-muted)" }}>Account number</dt>
              <dd className="font-semibold" style={{ color: "var(--black)" }}>{bank.account_number}</dd>
            </dl>
          </div>
        )}

        {/* Cash Info */}
        {paymentMethod === "cash" && (
          <div className="p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
            <p className="text-sm mb-2" style={{ color: "var(--text-muted)" }}>
              {fulfilment === "pickup" ? "Pay when you collect your order." : "Pay with cash when your order is delivered."}
            </p>
            <p className="text-xs font-semibold" style={{ color: "var(--black)" }}>
              {fulfilment === "pickup" ? "Your order reference is all you need at the counter." : "Please have the exact amount ready for the delivery rider."}
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
