"use client";

import { Check, MapPin, CreditCard, Eye } from "lucide-react";

interface CheckoutProgressCompactProps {
  currentStep: number;
}

const STEPS = [
  { number: 1, label: "Delivery", icon: MapPin },
  { number: 2, label: "Payment", icon: CreditCard },
  { number: 3, label: "Review", icon: Eye },
];

export default function CheckoutProgressCompact({ currentStep }: CheckoutProgressCompactProps) {
  return (
    <div className="flex items-center justify-between relative">
      {/* Progress Line */}
      <div className="absolute top-5 left-0 right-0 h-0.5" style={{ background: "var(--gray-mid)" }}>
        <div
          className="h-full transition-all duration-500"
          style={{
            background: "var(--red)",
            width: `${((currentStep - 1) / (STEPS.length - 1)) * 100}%`,
          }}
        />
      </div>

      {/* Steps */}
      {STEPS.map((step) => {
        const Icon = step.icon;
        const isCompleted = currentStep > step.number;
        const isCurrent = currentStep === step.number;

        return (
          <div key={step.number} className="relative flex flex-col items-center z-10">
            <div
              className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center transition-all duration-300 ${
                isCurrent ? "scale-110" : ""
              }`}
              style={{
                background: isCompleted || isCurrent ? "var(--red)" : "white",
                border: `3px solid ${isCompleted || isCurrent ? "var(--red)" : "var(--gray-mid)"}`,
                color: isCompleted || isCurrent ? "white" : "var(--text-muted)",
              }}
            >
              {isCompleted ? (
                <Check className="w-5 h-5 sm:w-6 sm:h-6" />
              ) : (
                <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
              )}
            </div>
            <p
              className={`text-xs sm:text-sm font-bold mt-2 ${
                isCurrent ? "scale-105" : ""
              } transition-all`}
              style={{ color: isCompleted || isCurrent ? "var(--black)" : "var(--text-muted)" }}
            >
              {step.label}
            </p>
          </div>
        );
      })}
    </div>
  );
}
