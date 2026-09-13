"use client";

import { useState } from "react";
import Link from "next/link";
import { User, Mail, Lock, Phone, Eye, EyeOff, UserPlus, Check, CheckCircle } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/authStore";
import SocialButtons from "./SocialButtons";

interface SignupFormProps {
  next: string | null;
  onDone: () => void;
  onSwitchToLogin: () => void;
}

/** The backend's minimum. The form used to say 8, which the API would reject. */
const MIN_PASSWORD_LENGTH = 10;

type FieldErrors = Partial<Record<"full_name" | "email" | "phone" | "password" | "confirmPassword" | "accept_terms", string>>;

function Checkbox({
  id,
  checked,
  onChange,
  children,
}: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: React.ReactNode;
}) {
  // A real checkbox, visually hidden, drives the existing styled box — so it is
  // reachable by keyboard and announced by screen readers. The old version was a
  // clickable <div> that neither could use.
  return (
    <label htmlFor={id} className="flex items-start gap-3 cursor-pointer">
      <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="peer sr-only" />
      <span
        aria-hidden="true"
        className="w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all peer-focus-visible:ring-2 peer-focus-visible:ring-offset-2"
        style={{
          borderColor: checked ? "var(--red)" : "var(--gray-mid)",
          background: checked ? "var(--red)" : "white",
        }}
      >
        {checked && <Check className="w-3 h-3 text-white" />}
      </span>
      <span className="text-sm" style={{ color: "var(--text-muted)" }}>
        {children}
      </span>
    </label>
  );
}

export default function SignupForm({ next, onDone, onSwitchToLogin }: SignupFormProps) {
  const register = useAuthStore((state) => state.register);

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    acceptTerms: false,
    subscribeNewsletter: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const errors: FieldErrors = {};
    if (formData.password.length < MIN_PASSWORD_LENGTH) {
      errors.password = `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
    }
    if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = "The passwords don't match.";
    }
    if (!formData.acceptTerms) {
      errors.accept_terms = "Please accept the Terms of Service and Privacy Policy to continue.";
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setIsLoading(true);
    try {
      await register({
        full_name: formData.name.trim(),
        email: formData.email.trim(),
        phone: formData.phone.trim(),
        password: formData.password,
        accept_terms: formData.acceptTerms,
        marketing_opt_in: formData.subscribeNewsletter,
      });
      setRegisteredEmail(formData.email.trim());
    } catch (err) {
      if (err instanceof ApiError && err.code === "validation_error") {
        setFieldErrors(err.fieldErrors as FieldErrors);
        if (err.fieldErrors.non_field_errors) setFormError(err.fieldErrors.non_field_errors);
      } else {
        setFormError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (registeredEmail) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "#10b98115" }}>
          <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />
        </div>
        <h3 className="font-black text-xl mb-2" style={{ color: "var(--black)" }}>
          Confirm Your Email
        </h3>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          We&apos;ve sent a confirmation link to <strong>{registeredEmail}</strong>. Follow it to finish
          creating your account — you&apos;ll be signed in straight away.
        </p>
        <button
          type="button"
          onClick={onDone}
          className="w-full px-6 py-3 rounded-lg font-bold transition-all hover:opacity-90"
          style={{ background: "var(--red)", color: "white" }}
        >
          Got It
        </button>
        <div className="mt-6 p-4 rounded-lg" style={{ background: "var(--gray-light)" }}>
          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
            Didn&apos;t receive it? Check your spam folder, or sign in with this email and we&apos;ll offer to send it again.
          </p>
        </div>
      </div>
    );
  }

  const errorText = (field: keyof FieldErrors) =>
    fieldErrors[field] ? (
      <p id={`signup-${field}-error`} className="text-xs font-semibold mt-1" style={{ color: "var(--red)" }}>
        {fieldErrors[field]}
      </p>
    ) : null;

  return (
    <div>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Create your account to start ordering delicious meals
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Full Name */}
        <div>
          <label htmlFor="signup-name" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Full Name
          </label>
          <div className="relative">
            <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              id="signup-name"
              type="text"
              autoComplete="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="John Doe"
              required
              aria-invalid={Boolean(fieldErrors.full_name)}
              className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: fieldErrors.full_name ? "var(--red)" : "var(--gray-mid)" }}
            />
          </div>
          {errorText("full_name")}
        </div>

        {/* Email & Phone */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="signup-email" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Email
            </label>
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
              <input
                id="signup-email"
                type="email"
                autoComplete="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="you@example.com"
                required
                aria-invalid={Boolean(fieldErrors.email)}
                className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
                style={{ borderColor: fieldErrors.email ? "var(--red)" : "var(--gray-mid)" }}
              />
            </div>
            {errorText("email")}
          </div>
          <div>
            <label htmlFor="signup-phone" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Phone
            </label>
            <div className="relative">
              <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
              <input
                id="signup-phone"
                type="tel"
                autoComplete="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+234 123 456 7890"
                required
                aria-invalid={Boolean(fieldErrors.phone)}
                className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
                style={{ borderColor: fieldErrors.phone ? "var(--red)" : "var(--gray-mid)" }}
              />
            </div>
            {errorText("phone")}
          </div>
        </div>

        {/* Password */}
        <div>
          <label htmlFor="signup-password" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              id="signup-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="••••••••"
              required
              minLength={MIN_PASSWORD_LENGTH}
              aria-invalid={Boolean(fieldErrors.password)}
              className="w-full pl-12 pr-12 py-3 rounded-lg border font-semibold"
              style={{ borderColor: fieldErrors.password ? "var(--red)" : "var(--gray-mid)" }}
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
          {fieldErrors.password ? errorText("password") : (
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Must be at least {MIN_PASSWORD_LENGTH} characters
            </p>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label htmlFor="signup-confirm" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Confirm Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              id="signup-confirm"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              placeholder="••••••••"
              required
              aria-invalid={Boolean(fieldErrors.confirmPassword)}
              className="w-full pl-12 pr-12 py-3 rounded-lg border font-semibold"
              style={{ borderColor: fieldErrors.confirmPassword ? "var(--red)" : "var(--gray-mid)" }}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              className="absolute right-4 top-1/2 -translate-y-1/2"
            >
              {showConfirmPassword ? (
                <EyeOff className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
              ) : (
                <Eye className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
              )}
            </button>
          </div>
          {errorText("confirmPassword")}
        </div>

        {/* Checkboxes */}
        <div className="space-y-3">
          <div>
            <Checkbox
              id="signup-terms"
              checked={formData.acceptTerms}
              onChange={(checked) => setFormData({ ...formData, acceptTerms: checked })}
            >
              I accept the{" "}
              <Link href="/terms" target="_blank" className="font-bold" style={{ color: "var(--red)" }}>
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link href="/privacy" target="_blank" className="font-bold" style={{ color: "var(--red)" }}>
                Privacy Policy
              </Link>
            </Checkbox>
            {errorText("accept_terms")}
          </div>

          <Checkbox
            id="signup-marketing"
            checked={formData.subscribeNewsletter}
            onChange={(checked) => setFormData({ ...formData, subscribeNewsletter: checked })}
          >
            Send me exclusive offers and updates
          </Checkbox>
        </div>

        {formError && (
          <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>
            {formError}
          </p>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--red)", color: "white" }}
        >
          {isLoading ? (
            "Creating Account..."
          ) : (
            <>
              <UserPlus className="w-5 h-5" />
              Create Account
            </>
          )}
        </button>
      </form>

      <SocialButtons next={next} />

      {/* Switch to Login */}
      <div className="mt-6 text-center">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Already have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="font-bold transition-all hover:opacity-80"
            style={{ color: "var(--red)" }}
          >
            Sign In
          </button>
        </p>
      </div>
    </div>
  );
}
