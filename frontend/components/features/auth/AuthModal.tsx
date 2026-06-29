"use client";

import { useState } from "react";
import { X } from "lucide-react";
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";
import ForgotPasswordForm from "./ForgotPasswordForm";

type AuthView = "login" | "signup" | "forgot";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultView?: AuthView;
}

export default function AuthModal({ isOpen, onClose, defaultView = "login" }: AuthModalProps) {
  const [currentView, setCurrentView] = useState<AuthView>(defaultView);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.7)" }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl max-w-md w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b p-4 sm:p-6 flex items-center justify-between z-10" style={{ borderColor: "var(--gray-mid)" }}>
          <h2 className="font-black text-xl sm:text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            {currentView === "login" && "Welcome Back"}
            {currentView === "signup" && "Create Account"}
            {currentView === "forgot" && "Reset Password"}
          </h2>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
          >
            <X className="w-6 h-6" style={{ color: "var(--black)" }} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6">
          {currentView === "login" && (
            <LoginForm
              onSuccess={onClose}
              onSwitchToSignup={() => setCurrentView("signup")}
              onForgotPassword={() => setCurrentView("forgot")}
            />
          )}
          {currentView === "signup" && (
            <SignupForm
              onSuccess={onClose}
              onSwitchToLogin={() => setCurrentView("login")}
            />
          )}
          {currentView === "forgot" && (
            <ForgotPasswordForm
              onSuccess={() => setCurrentView("login")}
              onBackToLogin={() => setCurrentView("login")}
            />
          )}
        </div>
      </div>
    </div>
  );
}
