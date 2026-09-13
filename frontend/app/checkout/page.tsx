"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api/client";
import type { Branch } from "@/lib/api/types";
import { useAuthStore } from "@/lib/store/authStore";
import { useCartStore } from "@/lib/store/cartStore";
import {
  CheckoutProgress,
  DeliveryStep,
  PaymentStep,
  ReviewStep,
} from "@/components/features/checkout";
import type { DeliveryData } from "@/components/features/checkout/DeliveryStep";
import type { PaymentData } from "@/components/features/checkout/PaymentStep";

const STEPS = [
  { number: 1, label: "Delivery" },
  { number: 2, label: "Payment" },
  { number: 3, label: "Review" },
];

export default function CheckoutPage() {
  const router = useRouter();
  const cart = useCartStore((state) => state.cart);
  const cartStatus = useCartStore((state) => state.status);
  const authStatus = useAuthStore((state) => state.status);
  const [currentStep, setCurrentStep] = useState(1);
  const [deliveryData, setDeliveryData] = useState<DeliveryData | null>(null);
  const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const placing = useRef(false);

  useEffect(() => {
    let cancelled = false;
    api<Branch>("/core/branch/")
      .then((data) => {
        if (!cancelled) setBranch(data);
      })
      .catch(() => {
        /* steps degrade: pickup address and transfer details are simply not shown */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const ready = cartStatus === "ready" && authStatus !== "idle" && authStatus !== "loading";
  const isEmpty = !cart || cart.items.length === 0;

  // Back to the cart if there is nothing to check out — unless an order is being
  // placed, which empties the cart on the way to the order page.
  useEffect(() => {
    if (ready && isEmpty && !placing.current) router.push("/cart");
  }, [ready, isEmpty, router]);

  if (!ready || isEmpty) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20" style={{ background: "var(--off-white)" }}>
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Page Header */}
          <div className="mb-8 text-center">
            <h1
              className="font-black text-3xl sm:text-4xl mb-2"
              style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}
            >
              Checkout
            </h1>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              Complete your order in just a few steps
            </p>
          </div>

          {/* Progress Indicator */}
          <CheckoutProgress currentStep={currentStep} steps={STEPS} />

          {/* Step Content */}
          {currentStep === 1 && (
            <DeliveryStep
              initial={deliveryData}
              branch={branch}
              onNext={(data) => {
                setDeliveryData(data);
                setCurrentStep(2);
              }}
            />
          )}

          {currentStep === 2 && deliveryData && (
            <PaymentStep
              initial={paymentData}
              fulfilment={deliveryData.fulfilment}
              branch={branch}
              isSignedIn={authStatus === "authenticated"}
              onNext={(data) => {
                setPaymentData(data);
                setCurrentStep(3);
              }}
              onBack={() => setCurrentStep(1)}
            />
          )}

          {currentStep === 3 && deliveryData && paymentData && (
            <ReviewStep
              cart={cart}
              branch={branch}
              deliveryData={deliveryData}
              paymentData={paymentData}
              onBack={() => setCurrentStep(2)}
              onPlacingChange={(value) => {
                placing.current = value;
              }}
            />
          )}
        </div>
      </main>
    </div>
  );
}
