"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle, Eye, EyeOff, KeyRound, Loader2, Lock } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/authStore";
import { useAuthModalStore } from "@/lib/store/authModalStore";

const MIN_PASSWORD_LENGTH = 10;

function ResetPassword() {
  const params = useSearchParams();
  const uid = params.get("uid");
  const token = params.get("token");

  const confirmPasswordReset = useAuthStore((state) => state.confirmPasswordReset);
  const openAuth = useAuthModalStore((state) => state.open);

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(uid && token ? null : "This reset link is incomplete.");
  const [linkInvalid, setLinkInvalid] = useState(!(uid && token));
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uid || !token) return;
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Use at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (password !== confirm) {
      setError("The passwords don't match.");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await confirmPasswordReset({ uid, token, new_password: password });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError) {
        // Weak passwords come back as `invalid_token` with the validator's message,
        // so only treat it as a dead link when the message says so.
        const deadLink = err.code === "invalid_token" && /link/i.test(err.message);
        setLinkInvalid(deadLink);
        setError(err.fieldErrors.new_password ?? err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const heading = (text: string) => (
    <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
      {text}
    </h1>
  );

  if (done) {
    return (
      <div className="text-center">
        <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "#10b98115" }}>
          <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />
        </div>
        {heading("Password changed")}
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          For your security we&apos;ve signed you out everywhere. Sign in with your new password.
        </p>
        <button
          type="button"
          onClick={() => openAuth("login", "/account")}
          className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
          style={{ background: "var(--red)" }}
        >
          Sign In
        </button>
      </div>
    );
  }

  if (linkInvalid) {
    return (
      <div className="text-center">
        <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "rgba(217,4,41,0.08)" }}>
          <KeyRound className="w-8 h-8" style={{ color: "var(--red)" }} />
        </div>
        {heading("Link not valid")}
        <p role="alert" className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          {error ?? "This reset link is invalid or has expired."} Reset links last one hour and work once.
        </p>
        <button
          type="button"
          onClick={() => openAuth("forgot")}
          className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
          style={{ background: "var(--red)" }}
        >
          Request a New Link
        </button>
      </div>
    );
  }

  return (
    <div>
      {heading("Choose a new password")}
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Use at least {MIN_PASSWORD_LENGTH} characters. Signing in afterwards will sign you out on other devices.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="reset-password" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            New Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              id="reset-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full pl-12 pr-12 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-4 top-1/2 -translate-y-1/2"
            >
              {showPassword ? (
                <EyeOff className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
              ) : (
                <Eye className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
              )}
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="reset-confirm" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Confirm New Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              id="reset-confirm"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="••••••••"
              className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        {error && (
          <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--red)" }}
        >
          {isLoading ? "Saving..." : "Save New Password"}
        </button>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 pt-20 sm:pt-24 pb-16" style={{ background: "var(--off-white)" }}>
      <div className="bg-white rounded-xl border p-6 sm:p-8 max-w-md w-full" style={{ borderColor: "var(--gray-mid)" }}>
        <Suspense fallback={<Loader2 className="w-8 h-8 animate-spin mx-auto" style={{ color: "var(--red)" }} />}>
          <ResetPassword />
        </Suspense>
      </div>
    </div>
  );
}
