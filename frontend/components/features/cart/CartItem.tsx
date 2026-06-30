"use client";

import Image from "next/image";
import { Minus, Plus, X } from "lucide-react";
import { useCartStore, type CartItem as CartItemType } from "@/lib/store/cartStore";
import { IMAGES, type ImageKey } from "@/lib/assets/images";

interface CartItemProps {
  item: CartItemType;
}

export default function CartItem({ item }: CartItemProps) {
  const { updateQuantity, removeItem } = useCartStore();

  const imageSrc = item.imageKey
    ? IMAGES.menu[item.imageKey as ImageKey]
    : null;

  return (
    <div className="flex gap-4 p-4 bg-white rounded-xl border" style={{ borderColor: "var(--gray-mid)" }}>
      {/* Image */}
      <div
        className="relative w-20 h-20 sm:w-24 sm:h-24 rounded-lg overflow-hidden shrink-0"
        style={{ background: "var(--cream)" }}
      >
        {imageSrc ? (
          <Image
            src={imageSrc}
            alt={item.name}
            fill
            className="object-cover"
            sizes="96px"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-2xl">
            🍔
          </div>
        )}
      </div>

      {/* Details */}
      <div className="flex-1 flex flex-col justify-between min-w-0">
        <div>
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h3 className="font-bold text-sm sm:text-base truncate" style={{ color: "var(--black)" }}>
                {item.name}
              </h3>
              <p className="text-xs text-gray-500 line-clamp-1 mt-0.5">
                {item.description}
              </p>
            </div>
            <button
              onClick={() => removeItem(item.id)}
              className="p-1 hover:bg-gray-100 rounded transition-colors shrink-0"
              aria-label="Remove item"
            >
              <X className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
            </button>
          </div>

          {item.customizations && item.customizations.length > 0 && (
            <div className="mt-2">
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {item.customizations.join(", ")}
              </p>
            </div>
          )}
        </div>

        {/* Quantity and Price */}
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => updateQuantity(item.id, item.quantity - 1)}
              className="w-7 h-7 rounded-full flex items-center justify-center transition-all hover:opacity-80"
              style={{ background: "var(--gray-mid)" }}
              aria-label="Decrease quantity"
            >
              <Minus className="w-3.5 h-3.5" style={{ color: "var(--black)" }} />
            </button>
            <span className="w-8 text-center font-semibold text-sm" style={{ color: "var(--black)" }}>
              {item.quantity}
            </span>
            <button
              onClick={() => updateQuantity(item.id, item.quantity + 1)}
              className="w-7 h-7 rounded-full flex items-center justify-center transition-all hover:opacity-90"
              style={{ background: "var(--red)" }}
              aria-label="Increase quantity"
            >
              <Plus className="w-3.5 h-3.5 text-white" />
            </button>
          </div>

          <div className="font-black text-base sm:text-lg" style={{ color: "var(--red)" }}>
            ₦{(item.price * item.quantity).toFixed(2)}
          </div>
        </div>
      </div>
    </div>
  );
}
