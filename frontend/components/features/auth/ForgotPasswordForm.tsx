"use client";

import { useState } from "react";
import { Mail, ArrowLeft, Send, CheckCircle } from "lucide-react";

interface ForgotPasswordFormProps {
  onSuccess: () => void;
  onBackToLogin: () => void;
}

export default function ForgotPasswordForm({ onSuccess, onBackToLogin }: ForgotPasswordFormProps) {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      setEmailSent(true);
    }, 1000);
  };

  if (emailSent) {
    return (
      <div className="text-center py-8">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
          style={{ background: "#10b98115" }}
        >
          <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />
        </div>

        <h3 className="font-black text-xl mb-2" style={{ color: "var(--black)" }}>
          Check Your Email
        </h3>

        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          We've sent a password reset link to <strong>{email}</strong>
        </p>

        <div className="space-y-3">
          <button
            onClick={onSuccess}
            className="w-full px-6 py-3 rounded-lg font-bold transition-all hover:opacity-90"
            style={{ background: "var(--red)", color: "white" }}
          >
            Back to Login
          </button>

          <button
            onClick={() => setEmailSent(false)}
            className="w-full px-6 py-3 rounded-lg font-bold transition-all hover:opacity-90"
            style={{ background: "var(--gray-light)", color: "var(--black)" }}
          >
            Resend Email
          </button>
        </div>

        <div className="mt-6 p-4 rounded-lg" style={{ background: "var(--gray-light)" }}>
          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
            Didn't receive the email? Check your spam folder or try again.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={onBackToLogin}
        className="flex items-center gap-2 mb-6 font-bold text-sm transition-all hover:opacity-80"
        style={{ color: "var(--red)" }}
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Login
      </button>

      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Enter your email address and we'll send you a link to reset your password
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Email */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Email Address
          </label>
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--red)", color: "white" }}
        >
          {isLoading ? (
            "Sending..."
          ) : (
            <>
              <Send className="w-5 h-5" />
              Send Reset Link
            </>
          )}
        </button>
      </form>

      <div className="mt-6 p-4 rounded-lg" style={{ background: "var(--gray-light)" }}>
        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
          <span style={{ color: "var(--red)" }}>Note:</span> The reset link will expire in 1 hour for security reasons.
        </p>
      </div>
    </div>
  );
}
