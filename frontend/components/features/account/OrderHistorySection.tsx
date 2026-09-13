"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Package, Eye, Loader2 } from "lucide-react";
import { statusStyle, useOrderHistory } from "@/components/features/orders";

export default function OrderHistorySection() {
  const router = useRouter();
  const { orders, state, hasMore } = useOrderHistory(5);

  if (state === "loading") {
    return (
      <div className="bg-white rounded-xl border p-12 flex items-center justify-center gap-2" style={{ borderColor: "var(--gray-mid)" }} role="status">
        <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading your orders…</span>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="bg-white rounded-xl border p-12 text-center" style={{ borderColor: "var(--gray-mid)" }}>
        <p role="alert" className="text-sm" style={{ color: "var(--text-muted)" }}>We couldn&apos;t load your orders. Please refresh.</p>
      </div>
    );
  }

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
        const { icon: StatusIcon, color } = statusStyle(order.status);
        const href = `/orders/${encodeURIComponent(order.reference)}`;

        return (
          <div
            key={order.reference}
            className="bg-white rounded-xl border p-4 sm:p-6 transition-all hover:shadow-md"
            style={{ borderColor: "var(--gray-mid)" }}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <div>
                <h3 className="font-black text-lg mb-1" style={{ color: "var(--black)" }}>
                  Order #{order.reference}
                </h3>
                {order.placed_at && (
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    {new Date(order.placed_at).toLocaleDateString("en-NG", { month: "short", day: "numeric", year: "numeric" })}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div
                  className="px-3 py-1.5 rounded-full flex items-center gap-2 font-bold text-sm"
                  style={{ background: `color-mix(in srgb, ${color} 12%, transparent)`, color }}
                >
                  <StatusIcon className="w-4 h-4" />
                  {order.status_display}
                </div>
                <Link
                  href={href}
                  aria-label={`View order ${order.reference}`}
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
                  style={{ border: "1px solid var(--gray-mid)" }}
                >
                  <Eye className="w-4 h-4" />
                </Link>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs font-bold mb-1" style={{ color: "var(--text-muted)" }}>Items</p>
                <p className="font-bold text-sm" style={{ color: "var(--black)" }}>
                  {order.item_count} {order.item_count === 1 ? "item" : "items"}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold mb-1" style={{ color: "var(--text-muted)" }}>Total</p>
                <p className="font-black text-lg" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                  {order.total.display}
                </p>
              </div>
            </div>

            <Link
              href={href}
              className="block w-full text-center px-4 py-2.5 rounded-lg font-bold text-sm transition-all hover:opacity-80"
              style={{ background: "var(--gray-light)", color: "var(--black)" }}
            >
              View Details
            </Link>
          </div>
        );
      })}

      {hasMore && (
        <Link href="/orders" className="block text-center text-sm font-bold py-2" style={{ color: "var(--red)" }}>
          View all orders →
        </Link>
      )}
    </div>
  );
}
