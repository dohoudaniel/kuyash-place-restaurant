"use client";

import { useOrderHistoryStore } from "@/lib/store/orderHistoryStore";
import { Package, Clock, CheckCircle, Eye } from "lucide-react";
import { useRouter } from "next/navigation";

export default function OrderHistorySection() {
  const { orders } = useOrderHistoryStore();
  const router = useRouter();

  const statusConfig = {
    confirmed: { icon: Clock, label: "Confirmed", color: "var(--red)" },
    preparing: { icon: Package, label: "Preparing", color: "#f59e0b" },
    ontheway: { icon: Package, label: "On The Way", color: "#3b82f6" },
    delivered: { icon: CheckCircle, label: "Delivered", color: "#10b981" },
    cancelled: { icon: Clock, label: "Cancelled", color: "#6b7280" },
  };

  if (orders.length === 0) {
    return (
      <div className="bg-white rounded-xl border p-12 text-center" style={{ borderColor: "var(--gray-mid)" }}>
        <Package className="w-16 h-16 mx-auto mb-4" style={{ color: "var(--text-muted)" }} />
        <h3 className="font-black text-xl mb-2" style={{ color: "var(--black)" }}>No Orders Yet</h3>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          Start ordering to see your order history here
        </p>
        <button
          onClick={() => router.push("/menu")}
          className="px-6 py-3 rounded-lg font-bold transition-all hover:opacity-90"
          style={{ background: "var(--red)", color: "white" }}
        >
          Browse Menu
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {orders.map((order) => {
        const status = statusConfig[order.status];
        const StatusIcon = status.icon;

        return (
          <div
            key={order.orderId}
            className="bg-white rounded-xl border p-4 sm:p-6 transition-all hover:shadow-md"
            style={{ borderColor: "var(--gray-mid)" }}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <div>
                <h3 className="font-black text-lg mb-1" style={{ color: "var(--black)" }}>
                  Order #{order.orderId}
                </h3>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  {new Date(order.orderDate).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div
                  className="px-3 py-1.5 rounded-full flex items-center gap-2 font-bold text-sm"
                  style={{ background: `${status.color}15`, color: status.color }}
                >
                  <StatusIcon className="w-4 h-4" />
                  {status.label}
                </div>
                <button
                  onClick={() => router.push(`/orders/${order.orderId}`)}
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
                  style={{ border: "1px solid var(--gray-mid)" }}
                >
                  <Eye className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs font-bold mb-1" style={{ color: "var(--text-muted)" }}>Items</p>
                <p className="font-bold text-sm" style={{ color: "var(--black)" }}>
                  {order.items.length} {order.items.length === 1 ? "item" : "items"}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold mb-1" style={{ color: "var(--text-muted)" }}>Total</p>
                <p className="font-black text-lg" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                  ₦{order.pricing.total.toFixed(2)}
                </p>
              </div>
            </div>

            <button
              onClick={() => router.push(`/orders/${order.orderId}`)}
              className="w-full px-4 py-2.5 rounded-lg font-bold text-sm transition-all hover:opacity-80"
              style={{ background: "var(--gray-light)", color: "var(--black)" }}
            >
              View Details
            </button>
          </div>
        );
      })}
    </div>
  );
}
