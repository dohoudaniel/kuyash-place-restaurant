"use client";

import { useState } from "react";
import Image from "next/image";
import { Plus, Minus, Trash2, Heart, Package } from "lucide-react";
import { useCartStore, type CartItem } from "@/lib/store/cartStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";

interface CartItemCompactProps {
  item: CartItem;
}

export default function CartItemCompact({ item }: CartItemCompactProps) {
  const { updateQuantity, removeItem } = useCartStore();
  const { addItem: addToWishlist, isInWishlist } = useWishlistStore();
  const [showSaveConfirm, setShowSaveConfirm] = useState(false);

  const inWishlist = isInWishlist(item.id);

  const handleSaveForLater = () => {
    if (!inWishlist) {
      addToWishlist({
        id: item.id,
        name: item.name,
        description: item.description,
        price: `₦${item.price.toFixed(2)}`,
        imageKey: item.imageKey,
      });
    }
    removeItem(item.id);
    setShowSaveConfirm(true);
    setTimeout(() => setShowSaveConfirm(false), 2000);
  };

  return (
    <div className="flex gap-3 sm:gap-4 p-3 rounded-lg hover:bg-gray-50 transition-all" style={{ border: "1px solid var(--gray-mid)" }}>
      {/* Image */}
      <div className="shrink-0 w-20 h-20 sm:w-24 sm:h-24 rounded-lg overflow-hidden relative" style={{ background: "var(--cream)" }}>
        {item.imageKey ? (
          <Image
            src={`/assets/menu/${item.imageKey}.png`}
            alt={item.name}
            fill
            className="object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-3xl">🍽️</div>
        )}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div>
          <h3 className="font-bold text-sm sm:text-base truncate" style={{ color: "var(--black)" }}>
            {item.name}
          </h3>
          <p className="text-xs mt-0.5 line-clamp-1" style={{ color: "var(--text-muted)" }}>
            {item.description}
          </p>
        </div>

        {/* Actions Row */}
        <div className="flex items-center gap-2 mt-2">
          {/* Quantity */}
          <div className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={() => updateQuantity(item.id, Math.max(1, item.quantity - 1))}
              className="w-7 h-7 rounded-full flex items-center justify-center transition-all hover:opacity-80"
              style={{ background: "var(--gray-mid)" }}
              disabled={item.quantity <= 1}
            >
              <Minus className="w-3 h-3" />
            </button>
            <span className="w-8 text-center font-bold text-sm" style={{ color: "var(--black)" }}>
              {item.quantity}
            </span>
            <button
              onClick={() => updateQuantity(item.id, item.quantity + 1)}
              className="w-7 h-7 rounded-full flex items-center justify-center transition-all hover:opacity-90"
              style={{ background: "var(--red)" }}
            >
              <Plus className="w-3 h-3 text-white" />
            </button>
          </div>

          {/* Save for later */}
          <button
            onClick={handleSaveForLater}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold transition-all hover:bg-red-50"
            style={{ color: "var(--red)" }}
          >
            <Package className="w-3 h-3" />
            <span className="hidden sm:inline">Save</span>
          </button>

          {/* Remove */}
          <button
            onClick={() => removeItem(item.id)}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold transition-all hover:bg-red-50"
            style={{ color: "var(--red)" }}
          >
            <Trash2 className="w-3 h-3" />
            <span className="hidden sm:inline">Remove</span>
          </button>
        </div>
      </div>

      {/* Price */}
      <div className="shrink-0 text-right flex flex-col justify-between">
        <p className="font-black text-base sm:text-lg" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
          ₦{(item.price * item.quantity).toFixed(2)}
        </p>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          ₦{item.price.toFixed(2)} each
        </p>
      </div>

      {showSaveConfirm && (
        <div className="fixed top-24 right-4 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-semibold animate-slide-in-right shadow-lg z-50">
          Saved to wishlist!
        </div>
      )}
    </div>
  );
}
