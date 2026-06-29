"use client";

import { useState } from "react";
import { CreditCard, Wallet, Banknote, Gift, DollarSign, Heart } from "lucide-react";
import type { PaymentData } from "./PaymentStep";

interface PaymentStepCompactProps {
  onNext: (data: PaymentData) => void;
  onBack: () => void;
  initialData: PaymentData | null;
  tip: number;
  onTipChange: (tip: number) => void;
}

export default function PaymentStepCompact({ onNext, onBack, initialData, tip, onTipChange }: PaymentStepCompactProps) {
  const [formData, setFormData] = useState<PaymentData>(
    initialData || {
      method: "card",
      cardNumber: "",
      cardName: "",
      cardExpiry: "",
      cardCvv: "",
    }
  );

  const [errors, setErrors] = useState<Partial<Record<keyof PaymentData, string>>>({});

  const paymentMethods = [
    { id: "card", label: "Card", sublabel: "Credit/Debit", icon: CreditCard },
    { id: "transfer", label: "Transfer", sublabel: "Bank", icon: Wallet },
    { id: "cash", label: "Cash", sublabel: "On Delivery", icon: Banknote },
  ];

  const tipOptions = [
    { value: 0, label: "No Tip", emoji: "👍" },
    { value: 2, label: "₦2", emoji: "😊" },
    { value: 5, label: "₦5", emoji: "😄" },
    { value: 10, label: "₦10", emoji: "🤩" },
  ];

  const validate = () => {
    const newErrors: Partial<Record<keyof PaymentData, string>> = {};

    if (formData.method === "card") {
      if (!formData.cardNumber || formData.cardNumber.length < 16) newErrors.cardNumber = "Invalid card number";
      if (!formData.cardName?.trim()) newErrors.cardName = "Required";
      if (!formData.cardExpiry || formData.cardExpiry.length < 4) newErrors.cardExpiry = "Invalid date";
      if (!formData.cardCvv || formData.cardCvv.length < 3) newErrors.cardCvv = "Invalid CVV";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onNext(formData);
    }
  };

  const formatCardNumber = (value: string) => {
    return value.replace(/\s/g, "").replace(/(\d{4})/g, "$1 ").trim();
  };

  const formatExpiry = (value: string) => {
    return value.replace(/\D/g, "").replace(/(\d{2})(\d)/, "$1/$2").slice(0, 5);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h2 className="font-black text-xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Payment Information
        </h2>

        {/* Payment Methods - Horizontal Cards */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {paymentMethods.map((method) => {
            const Icon = method.icon;
            return (
              <button
                key={method.id}
                type="button"
                onClick={() => setFormData({ ...formData, method: method.id as any })}
                className="p-4 rounded-xl border-2 transition-all text-center hover:shadow-md"
                style={{
                  borderColor: formData.method === method.id ? "var(--red)" : "var(--gray-mid)",
                  background: formData.method === method.id ? "rgba(217,4,41,0.05)" : "white",
                }}
              >
                <Icon className="w-6 h-6 mx-auto mb-2" style={{ color: formData.method === method.id ? "var(--red)" : "var(--text-muted)" }} />
                <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{method.label}</p>
                <p className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>{method.sublabel}</p>
              </button>
            );
          })}
        </div>

        {/* Card Details */}
        {formData.method === "card" && (
          <div className="space-y-3 p-4 rounded-xl mb-6" style={{ background: "rgba(217,4,41,0.02)", border: "1px solid var(--gray-mid)" }}>
            <div>
              <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>
                <CreditCard className="w-3 h-3 inline mr-1" />
                Card Number
              </label>
              <input
                type="text"
                value={formatCardNumber(formData.cardNumber || "")}
                onChange={(e) => setFormData({ ...formData, cardNumber: e.target.value.replace(/\s/g, "").slice(0, 16) })}
                className="w-full px-4 py-2.5 text-sm rounded-lg border outline-none transition-colors focus:border-red-500 font-mono"
                style={{ borderColor: errors.cardNumber ? "#ef4444" : "var(--gray-mid)" }}
                placeholder="1234 5678 9012 3456"
                maxLength={19}
              />
            </div>

            <div>
              <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>Cardholder Name</label>
              <input
                type="text"
                value={formData.cardName || ""}
                onChange={(e) => setFormData({ ...formData, cardName: e.target.value })}
                className="w-full px-4 py-2.5 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
                style={{ borderColor: errors.cardName ? "#ef4444" : "var(--gray-mid)" }}
                placeholder="JOHN DOE"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>Expiry Date</label>
                <input
                  type="text"
                  value={formatExpiry(formData.cardExpiry || "")}
                  onChange={(e) => setFormData({ ...formData, cardExpiry: e.target.value.replace(/\D/g, "").slice(0, 4) })}
                  className="w-full px-4 py-2.5 text-sm rounded-lg border outline-none transition-colors focus:border-red-500 font-mono"
                  style={{ borderColor: errors.cardExpiry ? "#ef4444" : "var(--gray-mid)" }}
                  placeholder="MM/YY"
                  maxLength={5}
                />
              </div>
              <div>
                <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--black)" }}>CVV</label>
                <input
                  type="text"
                  value={formData.cardCvv || ""}
                  onChange={(e) => setFormData({ ...formData, cardCvv: e.target.value.replace(/\D/g, "").slice(0, 4) })}
                  className="w-full px-4 py-2.5 text-sm rounded-lg border outline-none transition-colors focus:border-red-500 font-mono"
                  style={{ borderColor: errors.cardCvv ? "#ef4444" : "var(--gray-mid)" }}
                  placeholder="123"
                  maxLength={4}
                />
              </div>
            </div>
          </div>
        )}

        {formData.method === "transfer" && (
          <div className="p-6 rounded-xl text-center mb-6" style={{ background: "rgba(217,4,41,0.05)", border: "1px solid var(--gray-mid)" }}>
            <Wallet className="w-12 h-12 mx-auto mb-3" style={{ color: "var(--red)" }} />
            <h3 className="font-bold text-base mb-2" style={{ color: "var(--black)" }}>Bank Transfer Details</h3>
            <div className="inline-block text-left bg-white rounded-lg p-4 mt-3" style={{ border: "1px solid var(--gray-mid)" }}>
              <p className="text-xs mb-2"><span className="font-bold">Bank:</span> Kuyash Bank</p>
              <p className="text-xs mb-2"><span className="font-bold">Account:</span> 1234567890</p>
              <p className="text-xs"><span className="font-bold">Name:</span> Kuyash Place Restaurant</p>
            </div>
          </div>
        )}

        {formData.method === "cash" && (
          <div className="p-6 rounded-xl text-center mb-6" style={{ background: "rgba(217,4,41,0.05)", border: "1px solid var(--gray-mid)" }}>
            <Banknote className="w-12 h-12 mx-auto mb-3" style={{ color: "var(--red)" }} />
            <h3 className="font-bold text-base mb-2" style={{ color: "var(--black)" }}>Cash on Delivery</h3>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              Pay with cash when your order arrives. Please have exact change ready.
            </p>
          </div>
        )}

        {/* Tip Section - Visual Cards */}
        <div className="p-4 rounded-xl" style={{ background: "rgba(217,4,41,0.02)" }}>
          <div className="flex items-center gap-2 mb-3">
            <Heart className="w-4 h-4" style={{ color: "var(--red)" }} />
            <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>Add a Tip for Our Team?</h3>
          </div>
          <div className="grid grid-cols-4 gap-2">
            {tipOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onTipChange(option.value)}
                className="p-3 rounded-lg border-2 transition-all hover:shadow-md text-center"
                style={{
                  borderColor: tip === option.value ? "var(--red)" : "var(--gray-mid)",
                  background: tip === option.value ? "rgba(217,4,41,0.05)" : "white",
                }}
              >
                <div className="text-xl mb-1">{option.emoji}</div>
                <p className="font-bold text-xs" style={{ color: tip === option.value ? "var(--red)" : "var(--black)" }}>
                  {option.label}
                </p>
              </button>
            ))}
          </div>

          {/* Custom Tip */}
          <div className="mt-3">
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
              <input
                type="number"
                value={tip > 10 ? tip : ""}
                onChange={(e) => onTipChange(parseFloat(e.target.value) || 0)}
                className="flex-1 px-3 py-2 text-sm rounded-lg border outline-none transition-colors focus:border-red-500"
                style={{ borderColor: "var(--gray-mid)" }}
                placeholder="Custom amount"
                min="0"
                step="0.5"
              />
            </div>
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
          type="submit"
          className="flex-1 px-6 py-3 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
          style={{ background: "var(--red)" }}
        >
          Continue to Review
        </button>
      </div>
    </form>
  );
}
