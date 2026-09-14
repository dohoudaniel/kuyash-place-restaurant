"use client";

import { create } from "zustand";
import { api, clearCartToken, hasCartToken } from "@/lib/api/client";
import type { Cart } from "@/lib/api/types";

/**
 * The cart, as the server holds it.
 *
 * Replaces a localStorage array that did its own price, discount, VAT and
 * delivery arithmetic. Every total shown to the customer now comes from the API
 * response; this store holds that response and nothing it computed itself.
 */
export type CartLoadStatus = "idle" | "loading" | "ready" | "error";

export interface AddToCartInput {
  menu_item: string;
  quantity?: number;
  variant?: string | null;
  modifiers?: { modifier: string; quantity?: number }[];
  special_instructions?: string;
}

export interface FulfilmentInput {
  fulfilment_type?: "delivery" | "pickup";
  delivery_address?: string | null;
  /** Kobo. */
  tip?: number;
}

interface CartStore {
  cart: Cart | null;
  status: CartLoadStatus;
  /**
   * Load the cart. `onlyIfExisting` skips the request for a visitor who has
   * never added anything, so browsing the site does not create empty carts.
   */
  refresh: (options?: { onlyIfExisting?: boolean }) => Promise<void>;
  /** After sign-in: fold the anonymous cart into the account's cart. */
  adoptGuestCart: () => Promise<void>;
  addItem: (input: AddToCartInput) => Promise<Cart>;
  updateItem: (lineId: string, patch: { quantity?: number; special_instructions?: string }) => Promise<Cart>;
  removeItem: (lineId: string) => Promise<Cart>;
  applyPromo: (code: string) => Promise<Cart>;
  removePromo: () => Promise<Cart>;
  /** Apply a loyalty reward. Its points are spent when the order is placed. */
  applyReward: (rewardId: string) => Promise<Cart>;
  removeReward: () => Promise<Cart>;
  setFulfilment: (input: FulfilmentInput) => Promise<Cart>;
}

// Writes run one at a time. Each response is the whole cart, so two overlapping
// requests could otherwise land out of order and show a stale cart.
let queue: Promise<unknown> = Promise.resolve();
function serialised<T>(task: () => Promise<T>): Promise<T> {
  const run = queue.then(task, task);
  queue = run.catch(() => undefined);
  return run;
}

export const useCartStore = create<CartStore>()((set) => {
  const write = (path: string, init: Parameters<typeof api>[1]) =>
    serialised(async () => {
      const cart = await api<Cart>(path, init);
      set({ cart, status: "ready" });
      return cart;
    });

  return {
    cart: null,
    status: "idle",

    refresh: async ({ onlyIfExisting = false } = {}) => {
      if (onlyIfExisting && !hasCartToken()) {
        set({ cart: null, status: "ready" });
        return;
      }
      set((state) => ({ status: state.cart ? state.status : "loading" }));
      try {
        const cart = await serialised(() => api<Cart>("/cart/"));
        set({ cart, status: "ready" });
      } catch {
        set({ status: "error" });
      }
    },

    adoptGuestCart: async () => {
      try {
        const cart = await serialised(async () => {
          if (!hasCartToken()) return api<Cart>("/cart/");
          const merged = await api<Cart>("/cart/merge/", { method: "POST" });
          // The guest cart now lives inside the account's cart.
          clearCartToken();
          return merged;
        });
        set({ cart, status: "ready" });
      } catch {
        set({ status: "error" });
      }
    },

    addItem: (input) =>
      write("/cart/items/", {
        method: "POST",
        body: {
          menu_item: input.menu_item,
          quantity: input.quantity ?? 1,
          variant: input.variant ?? null,
          modifiers: (input.modifiers ?? []).map((choice) => ({
            modifier: choice.modifier,
            quantity: choice.quantity ?? 1,
          })),
          special_instructions: input.special_instructions ?? "",
        },
      }),

    updateItem: (lineId, patch) => write(`/cart/items/${lineId}/`, { method: "PATCH", body: patch }),

    removeItem: (lineId) => write(`/cart/items/${lineId}/`, { method: "DELETE" }),

    applyPromo: (code) => write("/cart/promo/", { method: "POST", body: { code } }),

    removePromo: () => write("/cart/promo/", { method: "DELETE" }),
    applyReward: (rewardId) => write(`/loyalty/rewards/${encodeURIComponent(rewardId)}/redeem/`, { method: "POST" }),
    removeReward: () => write("/loyalty/rewards/applied/", { method: "DELETE" }),

    setFulfilment: (input) => write("/cart/fulfilment/", { method: "PATCH", body: input }),
  };
});

/** Badge count. The server sums quantities; nothing is added up here. */
export const selectCartCount = (state: CartStore) => state.cart?.item_count ?? 0;
