"use client";

import { useEffect, useRef } from "react";
import { useAuthStore, type AuthStatus } from "@/lib/store/authStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";

/** Moves the wishlist onto the account at sign-in and off it at sign-out. */
export default function WishlistSync() {
  const status = useAuthStore((state) => state.status);
  const adoptAccount = useWishlistStore((state) => state.adoptAccount);
  const releaseAccount = useWishlistStore((state) => state.releaseAccount);
  const previous = useRef<AuthStatus>("idle");

  useEffect(() => {
    const before = previous.current;
    previous.current = status;
    if (status === "authenticated" && before !== "authenticated") void adoptAccount();
    else if (status === "anonymous" && before === "authenticated") releaseAccount();
  }, [status, adoptAccount, releaseAccount]);

  return null;
}
