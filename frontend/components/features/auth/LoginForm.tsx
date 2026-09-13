"use client";

import { useState } from "react";
import { Mail, Lock, Eye, EyeOff, LogIn, MailCheck } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/authStore";
import SocialButtons from "./SocialButtons";

interface LoginFormProps {
  next: string | null;
  onSuccess: () => void;
  onSwitchToSignup: () => void;
  onForgotPassword: () => void;
}

export default function LoginForm({ next, onSuccess, onSwitchToSignup, onForgotPassword }: LoginFormProps) {
  const login = useAuthStore((state) => state.login);
  const resendVerification = useAuthStore((state) => state.resendVerification);

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent">("idle");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setNeedsVerification(false);

    try {
      await login(formData);
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError && err.code === "email_not_verified") {
        setNeedsVerification(true);
      } else if (err instanceof ApiError) {
        setError(err.fieldErrors.email ?? err.fieldErrors.password ?? err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setResendState("sending");
    try {
      await resendVerification(formData.email);
      setResendState("sent");
    } catch (err) {
      setResendState("idle");
      setError(err instanceof ApiError ? err.message : "We couldn't send the email. Please try again.");
    }
  };

  return (
    <div>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Sign in to access your account and track your orders
      </p>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate={false}>
        {/* Email */}
        <div>
          <label htmlFor="login-email" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Email Address
          </label>
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="you@example.com"
              required
              className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label htmlFor="login-password" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              id="login-password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="••••••••"
              required
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

        {/* Forgot Password */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onForgotPassword}
            className="text-sm font-bold transition-all hover:opacity-80"
            style={{ color: "var(--red)" }}
          >
            Forgot Password?
          </button>
        </div>

        {error && (
          <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>
            {error}
          </p>
        )}

        {needsVerification && (
          <div role="alert" className="p-4 rounded-lg" style={{ background: "var(--off-white)" }}>
            <div className="flex gap-3">
              <MailCheck className="w-5 h-5 shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
              <div>
                <p className="text-sm font-bold" style={{ color: "var(--black)" }}>
                  Confirm your email first
                </p>
                <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                  {resendState === "sent"
                    ? "We've sent a new confirmation link. Check your inbox and spam folder."
                    : "Follow the link we emailed you, then sign in. Can't find it?"}
                </p>
                {resendState !== "sent" && (
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={resendState === "sending"}
                    className="text-sm font-bold mt-2 transition-all hover:opacity-80 disabled:opacity-50"
                    style={{ color: "var(--red)" }}
                  >
                    {resendState === "sending" ? "Sending..." : "Send the link again"}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--red)", color: "white" }}
        >
          {isLoading ? (
            "Signing in..."
          ) : (
            <>
              <LogIn className="w-5 h-5" />
              Sign In
            </>
          )}
        </button>
      </form>

      {/* Social Login */}
      <SocialButtons next={next} />

      {/* Switch to Signup */}
      <div className="mt-6 text-center">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Don&apos;t have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToSignup}
            className="font-bold transition-all hover:opacity-80"
            style={{ color: "var(--red)" }}
          >
            Sign Up
          </button>
        </p>
      </div>
    </div>
  );
}
