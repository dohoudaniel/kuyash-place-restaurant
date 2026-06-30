"use client";

import Image from "next/image";

interface OrderItem {
  id: string;
  name: string;
  description: string;
  price: number;
  quantity: number;
  imageKey?: string;
}

interface OrderDetailsProps {
  orderId: string;
  items: OrderItem[];
  orderDate: string;
}

export default function OrderDetails({ orderId, items, orderDate }: OrderDetailsProps) {
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-black text-xl sm:text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Order Details
        </h2>
        <div className="text-right">
          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Order ID</p>
          <p className="text-sm font-bold mt-0.5" style={{ color: "var(--black)" }}>{orderId}</p>
        </div>
      </div>

      <div className="mb-4">
        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
          Placed on {new Date(orderDate).toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit"
          })}
        </p>
      </div>

      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.id} className="flex gap-4 pb-4 border-b last:border-b-0" style={{ borderColor: "var(--gray-mid)" }}>
            {/* Image */}
            <div className="shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-lg overflow-hidden relative" style={{ background: "var(--off-white)" }}>
              {item.imageKey ? (
                <Image
                  src={`/assets/menu/${item.imageKey}.png`}
                  alt={item.name}
                  fill
                  className="object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-2xl">🍽️</div>
              )}
            </div>

            {/* Details */}
            <div className="flex-1 min-w-0">
              <h3 className="font-bold text-sm sm:text-base truncate" style={{ color: "var(--black)" }}>
                {item.name}
              </h3>
              <p className="text-xs sm:text-sm mt-1 line-clamp-1" style={{ color: "var(--text-muted)" }}>
                {item.description}
              </p>
              <p className="text-xs font-semibold mt-2" style={{ color: "var(--text-muted)" }}>
                Qty: {item.quantity}
              </p>
            </div>

            {/* Price */}
            <div className="text-right shrink-0">
              <p className="font-bold text-sm sm:text-base" style={{ color: "var(--black)" }}>
                ₦{(item.price * item.quantity).toFixed(2)}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                ₦{item.price.toFixed(2)} each
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Subtotal */}
      <div className="mt-6 pt-4 border-t" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex justify-between items-center">
          <p className="font-semibold" style={{ color: "var(--text-muted)" }}>Subtotal</p>
          <p className="font-bold text-lg" style={{ color: "var(--black)" }}>₦{subtotal.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
}
