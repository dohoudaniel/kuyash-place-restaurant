"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { Loader2, Lock, LogIn } from "lucide-react";
import { useAuthStore } from "@/lib/store/authStore";
import { useAuthModalStore } from "@/lib/store/authModalStore";

/**
 * Renders its children only for a signed-in customer.
 *
 * `proxy.ts` turns away visitors with no session cookie before the page loads,
 * but a cookie can outlive its session. This is the check that reads the
 * session itself. Neither is the security boundary — the API refuses the data
 * either way — they exist so nobody sees an empty account page.
 */
export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((state) => state.status);
  const openAuth = useAuthModalStore((state) => state.open);
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") openAuth("login", pathname);
  }, [status, openAuth, pathname]);

  if (status === "authenticated") return <>{children}</>;

  return (
    <div className="min-h-screen flex items-center justify-center px-4 pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      {status === "anonymous" ? (
        <div className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "rgba(217,4,41,0.08)" }}>
            <Lock className="w-6 h-6" style={{ color: "var(--red)" }} />
          </div>
          <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Sign in to continue
          </h1>
          <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
            You need to be signed in to see this page.
          </p>
          <button
            type="button"
            onClick={() => openAuth("login", pathname)}
            className="w-full px-6 py-3 rounded-full font-bold flex items-center justify-center gap-2 text-white transition-all hover:opacity-90"
            style={{ background: "var(--red)" }}
          >
            <LogIn className="w-5 h-5" />
            Sign In
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2" role="status">
          <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Checking your session…</span>
        </div>
      )}
    </div>
  );
}
