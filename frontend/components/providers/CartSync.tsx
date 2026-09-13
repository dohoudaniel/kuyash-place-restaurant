"use client";

import { useEffect, useRef } from "react";
import { useAuthStore, type AuthStatus } from "@/lib/store/authStore";
import { useCartStore } from "@/lib/store/cartStore";

/**
 * Keeps the cart in step with who is signed in.
 *
 * Signing in merges the anonymous cart into the account's, so nothing a visitor
 * added before signing in is lost. Signing out drops back to this browser's
 * anonymous cart, if it has one.
 */
export default function CartSync() {
  const status = useAuthStore((state) => state.status);
  const refresh = useCartStore((state) => state.refresh);
  const adoptGuestCart = useCartStore((state) => state.adoptGuestCart);
  const previous = useRef<AuthStatus>("idle");

  useEffect(() => {
    const before = previous.current;
    previous.current = status;
    if (status === "authenticated" && before !== "authenticated") {
      void adoptGuestCart();
    } else if (status === "anonymous" && before !== "anonymous") {
      void refresh({ onlyIfExisting: true });
    }
  }, [status, refresh, adoptGuestCart]);

  return null;
}
