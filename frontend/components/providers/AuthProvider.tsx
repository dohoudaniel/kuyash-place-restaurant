"use client";

import { Suspense, useEffect } from "react";
import { AuthModal } from "@/components/features/auth";
import { useAuthStore } from "@/lib/store/authStore";
import AuthQueryOpener from "./AuthQueryOpener";
import CartSync from "./CartSync";
import WishlistSync from "./WishlistSync";

/**
 * Reads the session once per page load and mounts the sign-in dialog once for
 * the whole app, so any screen can ask for sign-in.
 */
export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const bootstrap = useAuthStore((state) => state.bootstrap);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return (
    <>
      {children}
      <AuthModal />
      <CartSync />
      <WishlistSync />
      {/* useSearchParams needs a Suspense boundary so the rest of each page can still be prerendered. */}
      <Suspense fallback={null}>
        <AuthQueryOpener />
      </Suspense>
    </>
  );
}
