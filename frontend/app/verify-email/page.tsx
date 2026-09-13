"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle, Loader2, MailWarning } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/authStore";

type State = "verifying" | "verified" | "failed";

function VerifyEmail() {
  const key = useSearchParams().get("key");
  const verifyEmail = useAuthStore((state) => state.verifyEmail);
  const resendVerification = useAuthStore((state) => state.resendVerification);

  const [state, setState] = useState<State>(key ? "verifying" : "failed");
  const [message, setMessage] = useState(key ? "" : "This confirmation link is incomplete.");
  const [firstName, setFirstName] = useState("");
  const [email, setEmail] = useState("");
  const [resend, setResend] = useState<"idle" | "sending" | "sent">("idle");
  // React runs effects twice in development. A confirmation key must be sent
  // once, or the second request reports a failure for a link that just worked.
  const started = useRef(false);

  useEffect(() => {
    if (!key || started.current) return;
    started.current = true;
    verifyEmail(key)
      .then((user) => {
        setFirstName(user.full_name.split(" ")[0] ?? "");
        setState("verified");
      })
      .catch((err) => {
        setMessage(err instanceof ApiError ? err.message : "We couldn't confirm your email. Please try again.");
        setState("failed");
      });
  }, [key, verifyEmail]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    setResend("sending");
    try {
      await resendVerification(email.trim());
      setResend("sent");
    } catch (err) {
      setResend("idle");
      setMessage(err instanceof ApiError ? err.message : "We couldn't send the email. Please try again.");
    }
  };

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
      {state === "verifying" && (
        <div className="py-8 flex flex-col items-center gap-3" role="status">
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Confirming your email…</p>
        </div>
      )}

      {state === "verified" && (
        <>
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "#10b98115" }}>
            <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />
          </div>
          <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            {firstName ? `You're all set, ${firstName}` : "You're all set"}
          </h1>
          <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
            Your email is confirmed and you&apos;re signed in.
          </p>
          <Link
            href="/menu"
            className="block w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
            style={{ background: "var(--red)" }}
          >
            Browse the Menu
          </Link>
        </>
      )}

      {state === "failed" && (
        <>
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "rgba(217,4,41,0.08)" }}>
            <MailWarning className="w-8 h-8" style={{ color: "var(--red)" }} />
          </div>
          <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Link not valid
          </h1>
          <p role="alert" className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
            {message || "This confirmation link is invalid or has expired."}
          </p>

          {resend === "sent" ? (
            <p className="text-sm font-semibold" style={{ color: "var(--black)" }}>
              If that account still needs confirming, a new link is on its way.
            </p>
          ) : (
            <form onSubmit={handleResend} className="space-y-3 text-left">
              <label htmlFor="verify-email" className="block text-sm font-bold" style={{ color: "var(--black)" }}>
                Send a new link to
              </label>
              <input
                id="verify-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-4 py-3 rounded-lg border font-semibold"
                style={{ borderColor: "var(--gray-mid)" }}
              />
              <button
                type="submit"
                disabled={resend === "sending"}
                className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: "var(--red)" }}
              >
                {resend === "sending" ? "Sending..." : "Send New Link"}
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 pt-20 sm:pt-24 pb-16" style={{ background: "var(--off-white)" }}>
      <Suspense fallback={<Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} />}>
        <VerifyEmail />
      </Suspense>
    </div>
  );
}
