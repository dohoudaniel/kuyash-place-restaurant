"use client";

import { Check } from "lucide-react";

interface Step {
  number: number;
  label: string;
}

interface CheckoutProgressProps {
  currentStep: number;
  steps: Step[];
}

export default function CheckoutProgress({ currentStep, steps }: CheckoutProgressProps) {
  return (
    <div className="mb-8 sm:mb-12">
      <div className="flex items-center justify-between max-w-2xl mx-auto">
        {steps.map((step, index) => {
          const isCompleted = currentStep > step.number;
          const isCurrent = currentStep === step.number;
          const isUpcoming = currentStep < step.number;

          return (
            <div key={step.number} className="flex items-center flex-1">
              {/* Step Circle */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center font-bold text-sm sm:text-base transition-all duration-300 ${
                    isCompleted ? "text-white" : isCurrent ? "text-white" : ""
                  }`}
                  style={{
                    background: isCompleted || isCurrent ? "var(--red)" : "var(--gray-mid)",
                    color: isUpcoming ? "var(--text-muted)" : "white",
                  }}
                >
                  {isCompleted ? <Check className="w-5 h-5 sm:w-6 sm:h-6" /> : step.number}
                </div>
                <span
                  className={`mt-2 text-xs sm:text-sm font-semibold text-center transition-colors ${
                    isCurrent ? "font-bold" : ""
                  }`}
                  style={{ color: isCurrent ? "var(--red)" : isCompleted ? "var(--black)" : "var(--text-muted)" }}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div className="flex-1 h-0.5 mx-2 sm:mx-4" style={{ background: isCompleted ? "var(--red)" : "var(--gray-mid)" }} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
