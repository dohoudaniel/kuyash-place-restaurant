"use client";

import { useWishlistStore } from "@/lib/store/wishlistStore";
import { useCartStore } from "@/lib/store/cartStore";
import Image from "next/image";
import { ShoppingCart, X } from "lucide-react";

export default function SavedForLater() {
  const { items, removeItem } = useWishlistStore();
  const { addItem } = useCartStore();

  if (items.length === 0) return null;

  const handleMoveToCart = (item: typeof items[0]) => {
    const price = parseFloat(item.price.replace(/[^\d.]/g, ""));
    addItem({
      id: item.id,
      name: item.name,
      description: item.description,
      price,
      imageKey: item.imageKey,
    });
    removeItem(item.id);
  };

  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h3 className="font-bold text-sm mb-4 flex items-center gap-2" style={{ color: "var(--black)" }}>
        <span>Saved for Later</span>
        <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--cream)", color: "var(--text-muted)" }}>
          {items.length}
        </span>
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {items.slice(0, 6).map((item) => (
          <div
            key={item.id}
            className="relative group rounded-lg overflow-hidden border transition-all hover:shadow-lg"
            style={{ borderColor: "var(--gray-mid)" }}
          >
            <div className="relative w-full h-24 sm:h-28" style={{ background: "var(--cream)" }}>
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

              {/* Remove button */}
              <button
                onClick={() => removeItem(item.id)}
                className="absolute top-1 right-1 w-6 h-6 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all"
                style={{ background: "rgba(255,255,255,0.95)" }}
              >
                <X className="w-3 h-3" style={{ color: "var(--red)" }} />
              </button>
            </div>

            <div className="p-2">
              <h4 className="font-semibold text-xs truncate" style={{ color: "var(--black)" }}>
                {item.name}
              </h4>
              <div className="flex items-center justify-between mt-1">
                <span className="font-bold text-xs" style={{ color: "var(--red)" }}>
                  {item.price}
                </span>
                <button
                  onClick={() => handleMoveToCart(item)}
                  className="p-1 rounded transition-all hover:bg-red-50"
                  title="Move to cart"
                >
                  <ShoppingCart className="w-3 h-3" style={{ color: "var(--red)" }} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
