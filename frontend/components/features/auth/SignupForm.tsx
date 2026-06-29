"use client";

import { useState } from "react";
import { User, Mail, Lock, Phone, Eye, EyeOff, UserPlus, Check } from "lucide-react";

interface SignupFormProps {
  onSuccess: () => void;
  onSwitchToLogin: () => void;
}

export default function SignupForm({ onSuccess, onSwitchToLogin }: SignupFormProps) {
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      alert("Passwords don't match!");
      return;
    }

    if (!formData.acceptTerms) {
      alert("Please accept the terms and conditions");
      return;
    }

    setIsLoading(true);

    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      alert("Account created successfully!");
      onSuccess();
    }, 1000);
  };

  return (
    <div>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Create your account to start ordering delicious meals
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Full Name */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Full Name
          </label>
          <div className="relative">
            <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="John Doe"
              required
              className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        {/* Email & Phone */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Email
            </label>
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="you@example.com"
                required
                className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Phone
            </label>
            <div className="relative">
              <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+234 123 456 7890"
                required
                className="w-full pl-12 pr-4 py-3 rounded-lg border font-semibold"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>
          </div>
        </div>

        {/* Password */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              type={showPassword ? "text" : "password"}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="••••••••"
              required
              minLength={8}
              className="w-full pl-12 pr-12 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2"
            >
              {showPassword ? (
                <EyeOff className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
              ) : (
                <Eye className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
              )}
            </button>
          </div>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Must be at least 8 characters
          </p>
        </div>

        {/* Confirm Password */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Confirm Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              type={showConfirmPassword ? "text" : "password"}
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              placeholder="••••••••"
              required
              className="w-full pl-12 pr-12 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2"
            >
              {showConfirmPassword ? (
                <EyeOff className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
              ) : (
                <Eye className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
              )}
            </button>
          </div>
        </div>

        {/* Checkboxes */}
        <div className="space-y-3">
          <label className="flex items-start gap-3 cursor-pointer">
            <div
              className="w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all"
              style={{
                borderColor: formData.acceptTerms ? "var(--red)" : "var(--gray-mid)",
                background: formData.acceptTerms ? "var(--red)" : "white",
              }}
              onClick={() => setFormData({ ...formData, acceptTerms: !formData.acceptTerms })}
            >
              {formData.acceptTerms && <Check className="w-3 h-3 text-white" />}
            </div>
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
              I accept the{" "}
              <a href="/terms" className="font-bold" style={{ color: "var(--red)" }}>
                Terms of Service
              </a>{" "}
              and{" "}
              <a href="/privacy" className="font-bold" style={{ color: "var(--red)" }}>
                Privacy Policy
              </a>
            </span>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <div
              className="w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all"
              style={{
                borderColor: formData.subscribeNewsletter ? "var(--red)" : "var(--gray-mid)",
                background: formData.subscribeNewsletter ? "var(--red)" : "white",
              }}
              onClick={() => setFormData({ ...formData, subscribeNewsletter: !formData.subscribeNewsletter })}
            >
              {formData.subscribeNewsletter && <Check className="w-3 h-3 text-white" />}
            </div>
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
              Send me exclusive offers and updates
            </span>
          </label>
        </div>

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

      {/* Switch to Login */}
      <div className="mt-6 text-center">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Already have an account?{" "}
          <button
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
