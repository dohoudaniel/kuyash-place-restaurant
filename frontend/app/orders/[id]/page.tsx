"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { OrderStatus, OrderDetails, OrderSummary } from "@/components/features/orders";
import { ArrowLeft, Phone, MessageCircle } from "lucide-react";

// Mock data - in a real app, this would come from an API
interface OrderData {
  orderId: string;
  status: "confirmed" | "preparing" | "ontheway" | "delivered";
  orderDate: string;
  items: Array<{
    id: string;
    name: string;
    description: string;
    price: number;
    quantity: number;
    imageKey?: string;
  }>;
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

// Simulate fetching order data
function getOrderData(orderId: string): OrderData {
  // In a real app, this would be an API call
  return {
    orderId,
    status: "preparing",
    orderDate: new Date().toISOString(),
    items: [
      {
        id: "1",
        name: "Classic Burger",
        description: "Juicy beef patty with fresh lettuce, tomatoes, and special sauce",
        price: 14.90,
        quantity: 2,
        imageKey: "burger-1",
      },
      {
        id: "2",
        name: "Crispy Fries",
        description: "Golden crispy fries seasoned to perfection",
        price: 6.90,
        quantity: 1,
        imageKey: "fries-1",
      },
    ],
    deliveryAddress: {
      fullName: "John Doe",
      phone: "+1 555 123 4567",
      address: "123 Main Street, Apt 4B",
      city: "Lagos",
      state: "Lagos State",
      zipCode: "100001",
      deliveryNotes: "Please ring the doorbell twice",
    },
    paymentMethod: "card",
    pricing: {
      subtotal: 36.70,
      deliveryFee: 5.00,
      tax: 2.75,
      total: 44.45,
    },
  };
}

export default function OrderTrackingPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params.id as string;

  const [orderData, setOrderData] = useState<OrderData | null>(null);

  useEffect(() => {
    // Simulate API call
    const data = getOrderData(orderId);
    setOrderData(data);
  }, [orderId]);

  if (!orderData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 rounded-full animate-spin mx-auto mb-4"
            style={{ borderColor: "var(--gray-mid)", borderTopColor: "var(--red)" }} />
          <p className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>Loading order details...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-16">
        <div className="container-custom">
          {/* Back Button */}
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 mb-6 sm:mb-8 text-sm font-semibold transition-colors hover:opacity-70"
            style={{ color: "var(--black)" }}
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          {/* Page Header */}
          <div className="mb-8 sm:mb-12">
            <h1 className="font-black text-3xl sm:text-4xl lg:text-5xl mb-3"
              style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Track Your Order
            </h1>
            <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
              Your delicious meal is on its way! Track the status of your order below.
            </p>
          </div>

          {/* Content Grid */}
          <div className="grid lg:grid-cols-3 gap-6 sm:gap-8">
            {/* Left Column - Order Status & Details */}
            <div className="lg:col-span-2 space-y-6 sm:space-y-8">
              <OrderStatus status={orderData.status} />
              <OrderDetails
                orderId={orderData.orderId}
                items={orderData.items}
                orderDate={orderData.orderDate}
              />
            </div>

            {/* Right Column - Order Summary */}
            <div className="space-y-6 sm:space-y-8">
              <OrderSummary
                deliveryAddress={orderData.deliveryAddress}
                paymentMethod={orderData.paymentMethod}
                pricing={orderData.pricing}
              />

              {/* Contact Support */}
              <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
                <h3 className="font-bold text-base mb-4" style={{ color: "var(--black)" }}>Need Help?</h3>
                <div className="space-y-3">
                  <a
                    href="tel:+15559636366"
                    className="flex items-center gap-3 p-3 rounded-lg transition-all hover:bg-red-50"
                    style={{ border: "1px solid var(--gray-mid)" }}
                  >
                    <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "rgba(217,4,41,0.1)" }}>
                      <Phone className="w-5 h-5" style={{ color: "var(--red)" }} />
                    </div>
                    <div>
                      <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Call us</p>
                      <p className="text-sm font-bold" style={{ color: "var(--black)" }}>+1 555 96 36 36</p>
                    </div>
                  </a>

                  <button
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm text-white transition-all hover:opacity-90"
                    style={{ background: "var(--red)" }}
                  >
                    <MessageCircle className="w-4 h-4" />
                    Chat with Support
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
