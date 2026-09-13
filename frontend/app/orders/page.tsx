"use client";

import { RequireAuth } from "@/components/features/auth";
import { useRouter } from "next/navigation";
import { Package, Clock, CheckCircle, XCircle, ShoppingCart, Eye } from "lucide-react";
import { useOrderHistoryStore } from "@/lib/store/orderHistoryStore";
import { useCartStore } from "@/lib/store/cartStore";
import Image from "next/image";
import { useState } from "react";

const STATUS_CONFIG = {
  confirmed: { icon: Clock, label: "Confirmed", color: "var(--red)" },
  preparing: { icon: Package, label: "Preparing", color: "#f59e0b" },
  ontheway: { icon: Package, label: "On the Way", color: "#3b82f6" },
  delivered: { icon: CheckCircle, label: "Delivered", color: "#10b981" },
  cancelled: { icon: XCircle, label: "Cancelled", color: "#6b7280" },
};

function OrdersPage() {
  const router = useRouter();
  const { getAllOrders } = useOrderHistoryStore();
  const { addItem, clearCart } = useCartStore();
  const [reordering, setReordering] = useState<string | null>(null);

  const orders = getAllOrders();

  const handleReorder = (orderId: string) => {
    const order = orders.find((o) => o.orderId === orderId);
    if (!order) return;

    setReordering(orderId);
    clearCart();

    order.items.forEach((item) => {
      addItem({
        id: item.id,
        name: item.name,
        description: item.description,
        price: item.price,
        quantity: item.quantity,
        imageKey: item.imageKey,
      });
    });

    setTimeout(() => {
      setReordering(null);
      router.push("/cart");
    }, 800);
  };

  const handleViewOrder = (orderId: string) => {
    router.push(`/orders/${orderId}`);
  };

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-16">
        <div className="container-custom">
          {/* Page Header */}
          <div className="mb-8 sm:mb-12">
            <h1
              className="font-black text-3xl sm:text-4xl lg:text-5xl mb-3"
              style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}
            >
              Order History
            </h1>
            <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
              {orders.length} {orders.length === 1 ? "order" : "orders"} placed
            </p>
          </div>

          {orders.length === 0 ? (
            /* Empty State */
            <div className="flex flex-col items-center justify-center py-16 sm:py-24">
              <div
                className="w-24 h-24 sm:w-32 sm:h-32 rounded-full flex items-center justify-center mb-6"
                style={{ background: "rgba(217,4,41,0.1)" }}
              >
                <Package className="w-12 h-12 sm:w-16 sm:h-16" style={{ color: "var(--red)" }} />
              </div>
              <h2
                className="font-black text-2xl sm:text-3xl mb-3"
                style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}
              >
                No orders yet
              </h2>
              <p className="text-sm sm:text-base mb-8 text-center max-w-md" style={{ color: "var(--text-muted)" }}>
                Start your culinary journey by placing your first order
              </p>
              <a
                href="/#menu"
                className="px-8 py-3 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Browse Menu
              </a>
            </div>
          ) : (
            /* Orders List */
            <div className="space-y-6">
              {orders.map((order) => {
                const StatusIcon = STATUS_CONFIG[order.status].icon;

                return (
                  <div
                    key={order.orderId}
                    className="bg-white rounded-xl border p-6 transition-all hover:shadow-lg"
                    style={{ borderColor: "var(--gray-mid)" }}
                  >
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b mb-4"
                      style={{ borderColor: "var(--gray-mid)" }}>
                      <div>
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-bold text-base" style={{ color: "var(--black)" }}>
                            Order #{order.orderId}
                          </h3>
                          <span
                            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
                            style={{
                              background: `${STATUS_CONFIG[order.status].color}15`,
                              color: STATUS_CONFIG[order.status].color,
                            }}
                          >
                            <StatusIcon className="w-3.5 h-3.5" />
                            {STATUS_CONFIG[order.status].label}
                          </span>
                        </div>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                          Placed on {new Date(order.orderDate).toLocaleDateString("en-US", {
                            month: "long",
                            day: "numeric",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleViewOrder(order.orderId)}
                          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all hover:bg-gray-50"
                          style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </button>
                        {order.status === "delivered" && (
                          <button
                            onClick={() => handleReorder(order.orderId)}
                            disabled={reordering === order.orderId}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold text-white transition-all hover:opacity-90 disabled:opacity-50"
                            style={{ background: "var(--red)" }}
                          >
                            <ShoppingCart className="w-4 h-4" />
                            {reordering === order.orderId ? "Adding..." : "Reorder"}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Items Preview */}
                    <div className="space-y-3 mb-4">
                      {order.items.slice(0, 2).map((item) => (
                        <div key={item.id} className="flex items-center gap-3">
                          <div
                            className="shrink-0 w-14 h-14 rounded-lg overflow-hidden relative"
                            style={{ background: "var(--cream)" }}
                          >
                            {item.imageKey ? (
                              <Image
                                src={`/assets/menu/${item.imageKey}.png`}
                                alt={item.name}
                                fill
                                className="object-cover"
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center text-xl">🍽️</div>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-semibold text-sm truncate" style={{ color: "var(--black)" }}>
                              {item.name}
                            </h4>
                            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                              Qty: {item.quantity}
                            </p>
                          </div>
                          <p className="font-bold text-sm shrink-0" style={{ color: "var(--black)" }}>
                            ₦{(item.price * item.quantity).toFixed(2)}
                          </p>
                        </div>
                      ))}
                      {order.items.length > 2 && (
                        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
                          +{order.items.length - 2} more {order.items.length - 2 === 1 ? "item" : "items"}
                        </p>
                      )}
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: "var(--gray-mid)" }}>
                      <div>
                        <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>
                          {order.deliveryOption.charAt(0).toUpperCase() + order.deliveryOption.slice(1)} Delivery •{" "}
                          {order.paymentMethod === "card" ? "Card" : order.paymentMethod === "transfer" ? "Transfer" : "Cash on Delivery"}
                        </p>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                          {order.items.length} {order.items.length === 1 ? "item" : "items"}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>
                          Total
                        </p>
                        <p className="font-black text-lg" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                          ₦{order.pricing.total.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default function GuardedOrdersPage() {
  return (
    <RequireAuth>
      <OrdersPage />
    </RequireAuth>
  );
}
