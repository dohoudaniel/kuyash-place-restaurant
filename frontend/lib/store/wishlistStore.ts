import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Saved dishes, kept in this browser until the wishlist moves to the server
 * (integration step 10).
 *
 * Keyed by the dish's `slug` — the identifier the API uses — and `price` is the
 * display string exactly as the API sent it, so nothing here is ever parsed back
 * into a number.
 */
export interface WishlistItem {
  slug: string;
  name: string;
  description: string;
  /** `Money.display` at the time it was saved. The cart re-prices it. */
  price: string;
  imageUrl: string | null;
  addedAt: string;
}

interface WishlistStore {
  items: WishlistItem[];
  addItem: (item: Omit<WishlistItem, "addedAt">) => void;
  removeItem: (slug: string) => void;
  isInWishlist: (slug: string) => boolean;
  clearWishlist: () => void;
  getTotalItems: () => number;
}

export const useWishlistStore = create<WishlistStore>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (item) => {
        if (get().items.some((existing) => existing.slug === item.slug)) return;
        set({ items: [...get().items, { ...item, addedAt: new Date().toISOString() }] });
      },

      removeItem: (slug) => {
        set({ items: get().items.filter((item) => item.slug !== slug) });
      },

      isInWishlist: (slug) => get().items.some((item) => item.slug === slug),

      clearWishlist: () => set({ items: [] }),

      getTotalItems: () => get().items.length,
    }),
    {
      name: "kuyash-wishlist-storage",
      version: 2,
      // Version 1 stored mock dishes keyed by image name with dollar-figure
      // prices. None of them can be matched to a real menu item, so they go.
      migrate: (persisted, version) =>
        (version < 2 ? { items: [] } : persisted) as WishlistStore,
    }
  )
);
