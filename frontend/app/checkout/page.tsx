"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
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
  const { items, clearCart } = useCartStore();
  const [currentStep, setCurrentStep] = useState(1);
  const [deliveryData, setDeliveryData] = useState<DeliveryData | null>(null);
  const [paymentData, setPaymentData] = useState<PaymentData | null>(null);

  // Redirect to cart if no items
  useEffect(() => {
    if (items.length === 0) {
      router.push("/cart");
    }
  }, [items, router]);

  const handleDeliveryNext = (data: DeliveryData) => {
    setDeliveryData(data);
    setCurrentStep(2);
  };

  const handlePaymentNext = (data: PaymentData) => {
    setPaymentData(data);
    setCurrentStep(3);
  };

  const handleConfirmOrder = () => {
    // Generate order ID
    const orderId = `KYS-${Date.now().toString(36).toUpperCase()}`;

    // In a real app, you would:
    // 1. Send order data to backend API
    // 2. Process payment
    // 3. Create order in database
    // 4. Send confirmation email

    // Clear cart
    clearCart();

    // Redirect to order tracking page
    router.push(`/orders/${orderId}`);
  };

  if (items.length === 0) {
    return null; // Will redirect
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
          {currentStep === 1 && <DeliveryStep onNext={handleDeliveryNext} />}

          {currentStep === 2 && paymentData === null && (
            <PaymentStep
              onNext={handlePaymentNext}
              onBack={() => setCurrentStep(1)}
            />
          )}

          {currentStep === 3 && deliveryData && paymentData && (
            <ReviewStep
              deliveryData={deliveryData}
              paymentData={paymentData}
              onBack={() => setCurrentStep(2)}
              onConfirm={handleConfirmOrder}
            />
          )}
        </div>
      </main>
    </div>
  );
}
