"use client";

import { useState } from "react";
import { CreditCard, Plus, Trash2, Check } from "lucide-react";

interface PaymentMethod {
  id: string;
  type: "card";
  brand: "visa" | "mastercard";
  last4: string;
  expiry: string;
  isDefault: boolean;
}

export default function PaymentMethodsSection() {
  const [methods, setMethods] = useState<PaymentMethod[]>([
    {
      id: "1",
      type: "card",
      brand: "visa",
      last4: "4242",
      expiry: "12/25",
      isDefault: true,
    },
    {
      id: "2",
      type: "card",
      brand: "mastercard",
      last4: "5555",
      expiry: "08/26",
      isDefault: false,
    },
  ]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Payment Methods
        </h2>
        <button
          className="px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-all hover:opacity-90"
          style={{ background: "var(--red)", color: "white" }}
        >
          <Plus className="w-4 h-4" />
          Add Card
        </button>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {methods.map((method) => (
          <div
            key={method.id}
            className="bg-white rounded-xl border p-5 transition-all hover:shadow-md"
            style={{ borderColor: method.isDefault ? "var(--red)" : "var(--gray-mid)" }}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div
                  className="w-12 h-12 rounded-lg flex items-center justify-center"
                  style={{ background: "var(--gray-light)" }}
                >
                  <CreditCard className="w-6 h-6" style={{ color: "var(--black)" }} />
                </div>
                <div>
                  <h3 className="font-black text-base capitalize" style={{ color: "var(--black)" }}>
                    {method.brand}
                  </h3>
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    •••• {method.last4}
                  </p>
                </div>
              </div>
              <button className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-red-50">
                <Trash2 className="w-4 h-4" style={{ color: "var(--red)" }} />
              </button>
            </div>

            <div className="flex items-center justify-between pt-4" style={{ borderTop: "1px solid var(--gray-mid)" }}>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Expires {method.expiry}
              </p>
              {method.isDefault ? (
                <div className="flex items-center gap-1 text-xs font-bold" style={{ color: "var(--red)" }}>
                  <Check className="w-4 h-4" />
                  Default
                </div>
              ) : (
                <button
                  onClick={() => {
                    setMethods((prev) =>
                      prev.map((m) => ({ ...m, isDefault: m.id === method.id }))
                    );
                  }}
                  className="text-xs font-bold transition-all hover:opacity-80"
                  style={{ color: "var(--black)" }}
                >
                  Set as Default
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 rounded-lg" style={{ background: "var(--gray-light)" }}>
        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
          <span style={{ color: "var(--red)" }}>Secure:</span> Your payment information is encrypted and stored securely. We never share your card details.
        </p>
      </div>
    </div>
  );
}
