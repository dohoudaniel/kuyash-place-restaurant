"use client";

import { useState } from "react";
import Image from "next/image";
import { Plus, Minus, Trash2, Package, Loader2 } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { mediaUrl } from "@/lib/api/media";
import type { CartLine } from "@/lib/api/types";
import { useCartStore } from "@/lib/store/cartStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";

interface CartItemCompactProps {
  line: CartLine;
}

const MAX_QUANTITY = 99;

export default function CartItemCompact({ line }: CartItemCompactProps) {
  const updateItem = useCartStore((state) => state.updateItem);
  const removeItem = useCartStore((state) => state.removeItem);
  const { addItem: addToWishlist, isInWishlist } = useWishlistStore();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSaveConfirm, setShowSaveConfirm] = useState(false);

  const imageSrc = mediaUrl(line.menu_item.image_url);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const changeQuantity = (quantity: number) =>
    run(() => updateItem(line.id, { quantity: Math.min(MAX_QUANTITY, Math.max(1, quantity)) }));

  const handleSaveForLater = () =>
    run(async () => {
      if (!isInWishlist(line.menu_item.slug)) {
        addToWishlist({
          slug: line.menu_item.slug,
          name: line.menu_item.name,
          description: line.variant_name,
          price: line.unit_price.display,
          imageUrl: line.menu_item.image_url,
        });
      }
      await removeItem(line.id);
      setShowSaveConfirm(true);
      window.setTimeout(() => setShowSaveConfirm(false), 2000);
    });

  const details = [
    line.variant_name,
    ...line.modifiers.map((m) => (m.price_delta.amount > 0 ? `${m.name} (+${m.price_delta.display})` : m.name)),
  ].filter(Boolean);

  return (
    <div
      className="flex gap-3 sm:gap-4 p-3 rounded-lg hover:bg-gray-50 transition-all"
      style={{ border: `1px solid ${line.is_available ? "var(--gray-mid)" : "var(--red)"}`, opacity: busy ? 0.7 : 1 }}
    >
      {/* Image */}
      <div className="shrink-0 w-20 h-20 sm:w-24 sm:h-24 rounded-lg overflow-hidden relative" style={{ background: "var(--cream)" }}>
        {imageSrc ? (
          <Image src={imageSrc} alt={line.menu_item.name} fill sizes="96px" className="object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-3xl">🍽️</div>
        )}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0 flex flex-col justify-between">
        <div>
          <h3 className="font-bold text-sm sm:text-base truncate" style={{ color: "var(--black)" }}>
            {line.menu_item.name}
          </h3>
          {details.length > 0 && (
            <p className="text-xs mt-0.5 line-clamp-1" style={{ color: "var(--text-muted)" }}>
              {details.join(" · ")}
            </p>
          )}
          {line.special_instructions && (
            <p className="text-xs mt-0.5 line-clamp-1 italic" style={{ color: "var(--text-muted)" }}>
              “{line.special_instructions}”
            </p>
          )}
          {!line.is_available && (
            <p className="text-xs mt-0.5 font-semibold" style={{ color: "var(--red)" }}>
              {line.unavailable_reason || "No longer available"}
            </p>
          )}
          {error && (
            <p role="alert" className="text-xs mt-0.5 font-semibold" style={{ color: "var(--red)" }}>
              {error}
            </p>
          )}
        </div>

        {/* Actions Row */}
        <div className="flex items-center gap-2 mt-2">
          {/* Quantity */}
          <div className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={() => changeQuantity(line.quantity - 1)}
              aria-label={`Decrease quantity of ${line.menu_item.name}`}
              className="w-7 h-7 rounded-full flex items-center justify-center transition-all hover:opacity-80 disabled:opacity-40"
              style={{ background: "var(--gray-mid)" }}
              disabled={busy || line.quantity <= 1}
            >
              <Minus className="w-3 h-3" />
            </button>
            <span className="w-8 text-center font-bold text-sm" style={{ color: "var(--black)" }} aria-live="polite">
              {busy ? <Loader2 className="w-3 h-3 animate-spin inline" /> : line.quantity}
            </span>
            <button
              onClick={() => changeQuantity(line.quantity + 1)}
              aria-label={`Increase quantity of ${line.menu_item.name}`}
              className="w-7 h-7 rounded-full flex items-center justify-center transition-all hover:opacity-90 disabled:opacity-40"
              style={{ background: "var(--red)" }}
              disabled={busy || line.quantity >= MAX_QUANTITY || !line.is_available}
            >
              <Plus className="w-3 h-3 text-white" />
            </button>
          </div>

          {/* Save for later */}
          <button
            onClick={handleSaveForLater}
            disabled={busy}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold transition-all hover:bg-red-50"
            style={{ color: "var(--red)" }}
          >
            <Package className="w-3 h-3" />
            <span className="hidden sm:inline">Save</span>
          </button>

          {/* Remove */}
          <button
            onClick={() => run(() => removeItem(line.id))}
            disabled={busy}
            aria-label={`Remove ${line.menu_item.name}`}
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
          {line.line_subtotal.display}
        </p>
        <div>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            {line.unit_price.display} each
          </p>
          {line.discount.amount > 0 && (
            <p className="text-xs font-semibold" style={{ color: "var(--red)" }}>
              −{line.discount.display}
            </p>
          )}
        </div>
      </div>

      {showSaveConfirm && (
        <div role="status" className="fixed top-24 right-4 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-semibold animate-slide-in-right shadow-lg z-50">
          Saved to wishlist!
        </div>
      )}
    </div>
  );
}
