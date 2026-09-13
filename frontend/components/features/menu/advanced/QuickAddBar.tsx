"use client";

import { ShoppingCart, X, Check, Loader2 } from "lucide-react";
import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import type { MenuItemSummary } from "@/lib/api/types";
import { useCartStore } from "@/lib/store/cartStore";

interface QuickAddBarProps {
  selectedItems: MenuItemSummary[];
  onClear: () => void;
  /** Keeps only these dishes selected — the ones that need options chosen first. */
  onKeepSelected: (slugs: string[]) => void;
}

export default function QuickAddBar({ selectedItems, onClear, onKeepSelected }: QuickAddBarProps) {
  const addItem = useCartStore((state) => state.addItem);
  const [status, setStatus] = useState<"idle" | "adding" | "done">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const selectedCount = selectedItems.length;

  const handleAddAllToCart = async () => {
    setStatus("adding");
    setMessage(null);
    const needsOptions: MenuItemSummary[] = [];
    const failed: MenuItemSummary[] = [];

    for (const item of selectedItems) {
      try {
        await addItem({ menu_item: item.slug });
      } catch (err) {
        if (err instanceof ApiError && err.code === "cart_invalid") needsOptions.push(item);
        else failed.push(item);
      }
    }

    const leftOver = [...needsOptions, ...failed];
    if (leftOver.length === 0) {
      setStatus("done");
      // Confirmation only — every request has already completed.
      window.setTimeout(onClear, 1500);
      return;
    }

    setStatus("idle");
    setMessage(
      [
        needsOptions.length ? `${needsOptions.map((i) => i.name).join(", ")} need${needsOptions.length === 1 ? "s" : ""} options — open ${needsOptions.length === 1 ? "it" : "them"} to choose.` : "",
        failed.length ? `Couldn't add ${failed.map((i) => i.name).join(", ")}.` : "",
      ].filter(Boolean).join(" ")
    );
    onKeepSelected(leftOver.map((item) => item.slug));
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 animate-slide-up w-[calc(100%-2rem)] sm:w-auto">
      <div
        className="bg-white rounded-full shadow-2xl px-6 py-4 flex items-center gap-6"
        style={{ border: "2px solid var(--red)" }}
      >
        {/* Selected Count */}
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-white shrink-0"
            style={{ background: "var(--red)" }}
          >
            {selectedCount}
          </div>
          <div>
            <p className="text-sm font-bold" style={{ color: "var(--black)" }}>
              {selectedCount} item{selectedCount !== 1 ? "s" : ""} selected
            </p>
            <p role={message ? "alert" : undefined} className="text-xs" style={{ color: message ? "var(--red)" : "var(--text-muted)" }}>
              {message ?? "Prices are confirmed in your cart"}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={onClear}
            className="px-4 py-2 rounded-full text-sm font-semibold transition-all hover:bg-gray-100 flex items-center gap-1"
            style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
          >
            <X className="w-4 h-4 sm:hidden" />
            <span className="hidden sm:inline">Clear</span>
          </button>
          <button
            onClick={handleAddAllToCart}
            disabled={status !== "idle"}
            className="flex items-center gap-2 px-6 py-2 rounded-full text-sm font-bold text-white transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: status === "done" ? "var(--black)" : "var(--red)" }}
          >
            {status === "adding" ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Adding...
              </>
            ) : status === "done" ? (
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
