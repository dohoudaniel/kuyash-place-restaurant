"use client";

import { X } from "lucide-react";
import { useRouter } from "next/navigation";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Dialog, DialogClose, DialogOverlay, DialogPortal, DialogTitle } from "@/components/ui/dialog";
import { useAuthModalStore } from "@/lib/store/authModalStore";
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";
import ForgotPasswordForm from "./ForgotPasswordForm";

/**
 * The sign-in dialog, mounted once for the whole app.
 *
 * Built on the Dialog primitives so it traps focus, closes on Escape and is
 * announced as a dialog — the previous hand-rolled overlay did none of those.
 * The visual design is unchanged.
 */
export default function AuthModal() {
  const router = useRouter();
  const { isOpen, view, next, setView, close } = useAuthModalStore();

  const handleSignedIn = () => {
    const destination = next;
    close();
    if (destination) router.push(destination);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && close()}>
      <DialogPortal>
        <DialogOverlay className="bg-black/70 supports-backdrop-filter:backdrop-blur-none" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed top-1/2 left-1/2 z-50 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl w-[calc(100%-2rem)] max-w-md max-h-[90vh] overflow-y-auto outline-none"
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b p-4 sm:p-6 flex items-center justify-between z-10" style={{ borderColor: "var(--gray-mid)" }}>
            <DialogTitle className="font-black text-xl sm:text-2xl leading-normal" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              {view === "login" && "Welcome Back"}
              {view === "signup" && "Create Account"}
              {view === "forgot" && "Reset Password"}
            </DialogTitle>
            <DialogClose asChild>
              <button
                aria-label="Close"
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
              >
                <X className="w-6 h-6" style={{ color: "var(--black)" }} />
              </button>
            </DialogClose>
          </div>

          {/* Content */}
          <div className="p-4 sm:p-6">
            {view === "login" && (
              <LoginForm
                next={next}
                onSuccess={handleSignedIn}
                onSwitchToSignup={() => setView("signup")}
                onForgotPassword={() => setView("forgot")}
              />
            )}
            {view === "signup" && (
              <SignupForm
                next={next}
                onDone={close}
                onSwitchToLogin={() => setView("login")}
              />
            )}
            {view === "forgot" && (
              <ForgotPasswordForm
                onSuccess={() => setView("login")}
                onBackToLogin={() => setView("login")}
              />
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  );
}
