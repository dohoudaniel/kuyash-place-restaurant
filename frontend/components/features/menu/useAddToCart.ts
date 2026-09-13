"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import { useCartStore } from "@/lib/store/cartStore";

/**
 * One-tap "Add to cart" for a dish card.
 *
 * A card only knows the dish, not its options. If the dish needs a choice made
 * first (a required flavour, say) the server refuses with `cart_invalid`, and the
 * card opens the item dialog instead of showing an error.
 */
export function useAddToCart() {
  const addItem = useCartStore((state) => state.addItem);
  const [pending, setPending] = useState<string | null>(null);
  const [added, setAdded] = useState<string | null>(null);
  const [error, setError] = useState<{ slug: string; message: string } | null>(null);

  const add = async (slug: string, options: { onNeedsOptions?: () => void } = {}): Promise<boolean> => {
    setPending(slug);
    setError(null);
    try {
      await addItem({ menu_item: slug });
      setAdded(slug);
      // Confirmation only — the request has already completed.
      window.setTimeout(() => setAdded((current) => (current === slug ? null : current)), 2000);
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.code === "cart_invalid" && options.onNeedsOptions) {
        options.onNeedsOptions();
      } else {
        setError({ slug, message: err instanceof ApiError ? err.message : "Couldn't add that. Please try again." });
      }
      return false;
    } finally {
      setPending(null);
    }
  };

  return { add, pending, added, error };
}
