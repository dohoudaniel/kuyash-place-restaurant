"use client";

import { ShoppingCart, X, Check } from "lucide-react";
import { useState } from "react";
import { useCartStore } from "@/lib/store/cartStore";
import type { MenuItem } from "@/lib/types";

interface QuickAddBarProps {
  selectedCount: number;
  selectedItems: MenuItem[];
  onClear: () => void;
}

export default function QuickAddBar({ selectedCount, selectedItems, onClear }: QuickAddBarProps) {
  const { addItem } = useCartStore();
  const [isAdding, setIsAdding] = useState(false);

  const handleAddAllToCart = () => {
    setIsAdding(true);

    selectedItems.forEach((item) => {
      const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");
      const price = parseFloat(item.price.replace(/[^\d.]/g, ""));

      addItem({
        id: itemId,
        name: item.name,
        description: item.description,
        price,
        imageKey: item.imageKey,
      });
    });

    setTimeout(() => {
      setIsAdding(false);
      onClear();
    }, 1500);
  };

  const totalPrice = selectedItems.reduce((sum, item) => {
    return sum + parseFloat(item.price.replace(/[^\d.]/g, ""));
  }, 0);

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 animate-slide-up">
      <div
        className="bg-white rounded-full shadow-2xl px-6 py-4 flex items-center gap-6"
        style={{ border: "2px solid var(--red)" }}
      >
        {/* Selected Count */}
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-white"
            style={{ background: "var(--red)" }}
          >
            {selectedCount}
          </div>
          <div>
            <p className="text-sm font-bold" style={{ color: "var(--black)" }}>
              {selectedCount} item{selectedCount !== 1 ? "s" : ""} selected
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Total: ₦{totalPrice.toFixed(2)}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onClear}
            className="px-4 py-2 rounded-full text-sm font-semibold transition-all hover:bg-gray-100"
            style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
          >
            Clear
          </button>
          <button
            onClick={handleAddAllToCart}
            disabled={isAdding}
            className="flex items-center gap-2 px-6 py-2 rounded-full text-sm font-bold text-white transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: isAdding ? "var(--black)" : "var(--red)" }}
          >
            {isAdding ? (
              <>
                <Check className="w-4 h-4" />
                Added!
              </>
            ) : (
              <>
                <ShoppingCart className="w-4 h-4" />
                Add All to Cart
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
