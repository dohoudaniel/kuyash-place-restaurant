import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api/client";
import type { MenuItemSummary, Wishlist } from "@/lib/api/types";

/**
 * Saved dishes.
 *
 * Signed out, they live in this browser. Signed in, they live on the account —
 * so they survive a new phone or a cleared browser — and whatever was saved
 * while signed out is merged in on sign-in, never lost.
 *
 * Keyed by the dish's `slug`. `price` is the display string exactly as the API
 * sent it; nothing here parses it back into a number.
 */
export interface WishlistItem {
  slug: string;
  name: string;
  description: string;
  price: string;
  imageUrl: string | null;
  addedAt: string;
}

type Mode = "local" | "account";

interface WishlistStore {
  /** What screens render: the account's list when signed in, this browser's otherwise. */
  items: WishlistItem[];
  mode: Mode;
  /** This browser's list. The only part persisted, so no account's list is left on a shared device. */
  localItems: WishlistItem[];
  addItem: (item: Omit<WishlistItem, "addedAt">) => Promise<void>;
  removeItem: (slug: string) => Promise<void>;
  isInWishlist: (slug: string) => boolean;
  clearWishlist: () => Promise<void>;
  getTotalItems: () => number;
  /** On sign-in: merge this browser's list into the account, then show the account's. */
  adoptAccount: () => Promise<void>;
  /** On sign-out: back to this browser's (now empty) list. */
  releaseAccount: () => void;
}

function fromApi(item: MenuItemSummary): WishlistItem {
  return {
    slug: item.slug,
    name: item.name,
    description: item.description ?? "",
    price: item.price?.display ?? "",
    imageUrl: item.image_url,
    addedAt: "",
  };
}

const fromWishlist = (wishlist: Wishlist) => wishlist.items.map(fromApi);

export const useWishlistStore = create<WishlistStore>()(
  persist(
    (set, get) => ({
      items: [],
      mode: "local",
      localItems: [],

      addItem: async (item) => {
        if (get().items.some((existing) => existing.slug === item.slug)) return;
        const entry = { ...item, addedAt: new Date().toISOString() };

        if (get().mode === "local") {
          const localItems = [...get().localItems, entry];
          set({ localItems, items: localItems });
          return;
        }

        const previous = get().items;
        set({ items: [...previous, entry] }); // optimistic
        try {
          const wishlist = await api<Wishlist>("/wishlist/", { method: "POST", body: { menu_item: item.slug } });
          set({ items: fromWishlist(wishlist) });
        } catch {
          set({ items: previous });
        }
      },

      removeItem: async (slug) => {
        if (get().mode === "local") {
          const localItems = get().localItems.filter((item) => item.slug !== slug);
          set({ localItems, items: localItems });
          return;
        }

        const previous = get().items;
        set({ items: previous.filter((item) => item.slug !== slug) }); // optimistic
        try {
          const wishlist = await api<Wishlist>(`/wishlist/${encodeURIComponent(slug)}/`, { method: "DELETE" });
          set({ items: fromWishlist(wishlist) });
        } catch {
          set({ items: previous });
        }
      },

      isInWishlist: (slug) => get().items.some((item) => item.slug === slug),

      clearWishlist: async () => {
        if (get().mode === "local") {
          set({ localItems: [], items: [] });
          return;
        }
        for (const item of [...get().items]) {
          await get().removeItem(item.slug);
        }
      },

      getTotalItems: () => get().items.length,

      adoptAccount: async () => {
        const local = get().localItems;
        try {
          const wishlist = local.length
            ? await api<Wishlist>("/wishlist/sync/", { method: "POST", body: { menu_items: local.map((item) => item.slug) } })
            : await api<Wishlist>("/wishlist/");
          // Merged into the account, so this browser's copy is no longer needed.
          set({ mode: "account", items: fromWishlist(wishlist), localItems: [] });
        } catch {
          // Keep showing the local list rather than an empty one; try again next sign-in.
          set({ mode: "local", items: local });
        }
      },

      releaseAccount: () => set({ mode: "local", items: get().localItems }),
    }),
    {
      name: "kuyash-wishlist-storage",
      version: 3,
      partialize: (state) => ({ localItems: state.localItems }),
      // v1 stored mock dishes keyed by image name; v2 stored `items` directly.
      migrate: (persisted, version) => {
        if (version < 2) return { localItems: [] };
        if (version === 2) return { localItems: ((persisted as { items?: WishlistItem[] }).items ?? []) };
        return persisted as { localItems: WishlistItem[] };
      },
      merge: (persisted, current) => {
        const localItems = (persisted as { localItems?: WishlistItem[] } | undefined)?.localItems ?? [];
        return { ...current, localItems, items: current.mode === "local" ? localItems : current.items };
      },
    }
  )
);
