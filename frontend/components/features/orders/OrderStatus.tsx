"use client";

import type { OrderDetail } from "@/lib/api/types";
import { FINAL_STATUSES, formatTime, statusStyle } from "./statusStyles";

interface OrderStatusProps {
  order: OrderDetail;
}

const MESSAGES: Record<string, string> = {
  pending_payment: "We're waiting for your payment to be confirmed.",
  paid: "Payment received. The kitchen will confirm your order shortly.",
  confirmed: "Your order has been confirmed and will be prepared shortly.",
  preparing: "Our chefs are preparing your meal with care.",
  ready: "Your order is ready.",
  out_for_delivery: "Your order is on the way! Our rider will arrive soon.",
  delivered: "Your order has been delivered. Enjoy your meal!",
  cancelled: "This order was cancelled.",
  rejected: "The kitchen couldn't take this order. Any payment will be refunded.",
  expired: "This order expired before payment was completed.",
  refunded: "This order was refunded.",
  failed: "Something went wrong with this order. Please contact us.",
  failed_delivery: "We couldn't complete the delivery. We'll be in touch.",
};

/**
 * Progress from the order's own event log. The previous version showed a fixed
 * four-step list with times invented from the current clock.
 */
export default function OrderStatus({ order }: OrderStatusProps) {
  // Cash orders are confirmed straight away; they never pass through payment.
  const steps = order.timeline.filter(
    (step) => !(order.payment_method === "cash" && (step.status === "pending_payment" || step.status === "paid"))
  );
  const currentIndex = steps.reduce((last, step, index) => (step.reached ? index : last), -1);
  const isFinal = FINAL_STATUSES.has(order.status);
  const estimate = order.fulfilment_type === "delivery" ? order.estimated_delivery_at : order.estimated_ready_at;

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Order Status
      </h2>

      <ol className="space-y-6">
        {steps.map((step, index) => {
          const { icon: Icon } = statusStyle(step.status);
          const isCompleted = step.reached;
          const isCurrent = index === currentIndex;
          const isProblem = FINAL_STATUSES.has(step.status) && step.status !== "delivered";

          return (
            <li key={step.status} className="flex gap-4" aria-current={isCurrent ? "step" : undefined}>
              {/* Icon */}
              <div className="shrink-0">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
                    isCurrent && !isFinal ? "animate-pulse" : ""
                  }`}
                  style={{ background: isCompleted ? (isProblem ? "#6b7280" : "var(--red)") : "var(--gray-mid)" }}
                >
                  <Icon className="w-6 h-6" style={{ color: isCompleted ? "white" : "var(--text-muted)" }} />
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 pt-2">
                <p
                  className={`font-bold text-base ${isCurrent ? "text-lg" : ""}`}
                  style={{ color: isCompleted ? (isProblem ? "var(--black)" : "var(--red)") : "var(--text-muted)" }}
                >
                  {step.label}
                </p>
                <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                  {isCurrent && MESSAGES[step.status]}
                  {isCompleted && !isCurrent && "✓ Completed"}
                </p>
              </div>

              {/* Time */}
              {step.at && (
                <div className="text-xs font-semibold pt-2" style={{ color: "var(--text-muted)" }}>
                  {formatTime(step.at)}
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {/* Estimated Time */}
      {!isFinal && estimate && (
        <div className="mt-6 p-4 rounded-lg" style={{ background: "rgba(217,4,41,0.05)" }}>
          <p className="text-sm font-semibold" style={{ color: "var(--red)" }}>
            {order.fulfilment_type === "delivery" ? "Estimated delivery by" : "Estimated ready by"} {formatTime(estimate)}
          </p>
        </div>
      )}
    </div>
  );
}
