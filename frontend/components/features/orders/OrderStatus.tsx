"use client";

import { Check, Package, Truck, Home } from "lucide-react";

interface OrderStatusProps {
  status: "confirmed" | "preparing" | "ontheway" | "delivered";
}

export default function OrderStatus({ status }: OrderStatusProps) {
  const statuses = [
    { id: "confirmed", label: "Order Confirmed", icon: Check },
    { id: "preparing", label: "Preparing", icon: Package },
    { id: "ontheway", label: "On the Way", icon: Truck },
    { id: "delivered", label: "Delivered", icon: Home },
  ];

  const currentIndex = statuses.findIndex((s) => s.id === status);

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Order Status
      </h2>

      <div className="space-y-6">
        {statuses.map((step, index) => {
          const Icon = step.icon;
          const isCompleted = index <= currentIndex;
          const isCurrent = index === currentIndex;

          return (
            <div key={step.id} className="flex gap-4">
              {/* Icon */}
              <div className="shrink-0">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
                    isCurrent ? "animate-pulse" : ""
                  }`}
                  style={{
                    background: isCompleted ? "var(--red)" : "var(--gray-mid)",
                  }}
                >
                  <Icon className="w-6 h-6" style={{ color: isCompleted ? "white" : "var(--text-muted)" }} />
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 pt-2">
                <p
                  className={`font-bold text-base ${isCurrent ? "text-lg" : ""}`}
                  style={{ color: isCompleted ? "var(--red)" : "var(--text-muted)" }}
                >
                  {step.label}
                </p>
                <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                  {isCurrent && getStatusMessage(status)}
                  {isCompleted && !isCurrent && "✓ Completed"}
                </p>
              </div>

              {/* Time */}
              {isCompleted && (
                <div className="text-xs font-semibold pt-2" style={{ color: "var(--text-muted)" }}>
                  {getTimeForStatus(index)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Estimated Time */}
      {status !== "delivered" && (
        <div className="mt-6 p-4 rounded-lg" style={{ background: "rgba(217,4,41,0.05)" }}>
          <p className="text-sm font-semibold" style={{ color: "var(--red)" }}>
            Estimated delivery: {getEstimatedTime(status)}
          </p>
        </div>
      )}
    </div>
  );
}

function getStatusMessage(status: string): string {
  switch (status) {
    case "confirmed":
      return "Your order has been confirmed and will be prepared shortly.";
    case "preparing":
      return "Our chefs are preparing your delicious meal with care.";
    case "ontheway":
      return "Your order is on the way! Our rider will arrive soon.";
    case "delivered":
      return "Your order has been delivered. Enjoy your meal!";
    default:
      return "";
  }
}

function getTimeForStatus(index: number): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - (3 - index) * 10);
  return now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function getEstimatedTime(status: string): string {
  switch (status) {
    case "confirmed":
      return "30-40 minutes";
    case "preparing":
      return "20-30 minutes";
    case "ontheway":
      return "10-15 minutes";
    default:
      return "Soon";
  }
}
