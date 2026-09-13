"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, ShieldAlert } from "lucide-react";
import { safeNext } from "@/lib/auth/next";
import { useAuthStore } from "@/lib/store/authStore";
import { useAuthModalStore } from "@/lib/store/authModalStore";

/**
 * Explains the `?error=` codes the backend sends back, in words a customer can
 * act on. The first group are allauth's own (`AuthError` and the headless login
 * pipeline); `social_email_unverified` is Kuyash Place's takeover backstop.
 */
function describe(error: string): string {
  switch (error) {
    case "cancelled":
      return "Sign-in was cancelled. No changes were made.";
    case "denied":
      return "The provider didn't allow the sign-in. Please try again, or use your email and password.";
    case "social_email_unverified":
      return "An account with that email already exists. Sign in with your email and password instead — for your security we won't link it to a provider that hasn't verified the address.";
    case "signup_closed":
      return "New accounts can't be created right now. Please try again later.";
    case "permission_denied":
      return "This account can't sign in with that provider.";
    case "reauthentication_required":
      return "Please sign in with your password to confirm it's you, then try again.";
    default:
      return "We couldn't sign you in with that provider. Please try again or use your email and password.";
  }
}

function Callback() {
  const params = useSearchParams();
  const router = useRouter();
  const refresh = useAuthStore((state) => state.refresh);
  const openAuth = useAuthModalStore((state) => state.open);
  const next = safeNext(params.get("next"));
  const error = params.get("error");
  const [failed, setFailed] = useState<string | null>(error ? describe(error) : null);
  const handled = useRef(false);

  useEffect(() => {
    if (error || handled.current) return;
    handled.current = true;
    // The provider sent the customer back; the backend has set the session
    // cookie. Read it rather than assume it worked.
    refresh().then(() => {
      if (useAuthStore.getState().status === "authenticated") {
        router.replace(next);
      } else {
        setFailed(describe(""));
      }
    });
  }, [error, next, refresh, router]);

  if (!failed) {
    return (
      <div className="flex items-center gap-2" role="status">
        <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>Signing you in…</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "rgba(217,4,41,0.08)" }}>
        <ShieldAlert className="w-6 h-6" style={{ color: "var(--red)" }} />
      </div>
      <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Sign-in didn&apos;t complete
      </h1>
      <p role="alert" className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        {failed}
      </p>
      <button
        type="button"
        onClick={() => openAuth("login", next)}
        className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
        style={{ background: "var(--red)" }}
      >
        Try Again
      </button>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 pt-20 sm:pt-24 pb-16" style={{ background: "var(--off-white)" }}>
      <Suspense fallback={<Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />}>
        <Callback />
      </Suspense>
    </div>
  );
}
