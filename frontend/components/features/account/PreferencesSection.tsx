"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, Mail, Loader2, ShieldAlert, Check } from "lucide-react";
import { ApiError, api } from "@/lib/api/client";
import type { Profile } from "@/lib/api/types";
import { useAuthStore } from "@/lib/store/authStore";
import { useCartStore } from "@/lib/store/cartStore";

/**
 * What the account can actually control.
 *
 * The previous screen offered SMS, push notifications, a newsletter and four
 * languages; none of those exist, and "Save Preferences" only showed an alert.
 * What does exist is marketing consent (withdrawable, as NDPR requires), the fact
 * that order messages are always sent, and the right to erase the account.
 */
export default function PreferencesSection() {
  const router = useRouter();
  const endSession = useAuthStore((state) => state.endSession);
  const refreshCart = useCartStore((state) => state.refresh);

  const [marketing, setMarketing] = useState<boolean | null>(null);
  const [marketingState, setMarketingState] = useState<"idle" | "saving" | "saved">("idle");
  const [marketingError, setMarketingError] = useState<string | null>(null);

  const [confirmErase, setConfirmErase] = useState(false);
  const [understood, setUnderstood] = useState(false);
  const [erasing, setErasing] = useState(false);
  const [eraseError, setEraseError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<Profile>("/accounts/me/")
      .then((profile) => !cancelled && setMarketing(Boolean(profile.marketing_opt_in)))
      .catch(() => !cancelled && setMarketingError("We couldn't load your preferences. Please refresh."));
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleMarketing = async () => {
    if (marketing === null) return;
    const next = !marketing;
    setMarketing(next);
    setMarketingState("saving");
    setMarketingError(null);
    try {
      const profile = await api<Profile>("/accounts/me/", { method: "PATCH", body: { marketing_opt_in: next } });
      setMarketing(Boolean(profile.marketing_opt_in));
      setMarketingState("saved");
    } catch (err) {
      setMarketing(!next);
      setMarketingState("idle");
      setMarketingError(err instanceof ApiError ? err.message : "We couldn't save that. Please try again.");
    }
  };

  const eraseAccount = async () => {
    setErasing(true);
    setEraseError(null);
    try {
      await api<void>("/accounts/me/", { method: "DELETE" });
      endSession();
      void refreshCart({ onlyIfExisting: true });
      router.push("/");
    } catch (err) {
      setErasing(false);
      setEraseError(err instanceof ApiError ? err.message : "We couldn't delete your account. Please try again or contact us.");
    }
  };

  const toggle = (on: boolean, disabled = false) => (
    <span
      aria-hidden="true"
      className="relative w-12 h-6 rounded-full transition-all inline-block shrink-0"
      style={{ background: on ? "var(--red)" : "var(--gray-mid)", opacity: disabled ? 0.6 : 1 }}
    >
      <span className="absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all" style={{ left: on ? "26px" : "2px" }} />
    </span>
  );

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        {/* Order messages */}
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "rgba(217,4,41,0.08)" }}>
              <Bell className="w-5 h-5" style={{ color: "var(--red)" }} />
            </div>
            <h3 className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Notifications
            </h3>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-bold text-sm" style={{ color: "var(--black)" }}>Order Updates</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Confirmations, status changes and receipts, by email. Always on — they&apos;re part of your order.
              </p>
            </div>
            {toggle(true, true)}
          </div>
        </div>

        {/* Marketing */}
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "#3b82f615" }}>
              <Mail className="w-5 h-5" style={{ color: "#3b82f6" }} />
            </div>
            <h3 className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Marketing
            </h3>
          </div>

          <button
            type="button"
            role="switch"
            aria-checked={Boolean(marketing)}
            disabled={marketing === null || marketingState === "saving"}
            onClick={toggleMarketing}
            className="w-full flex items-center justify-between gap-4 text-left disabled:cursor-wait"
          >
            <span>
              <span className="block font-bold text-sm" style={{ color: "var(--black)" }}>Offers &amp; News</span>
              <span className="block text-xs" style={{ color: "var(--text-muted)" }}>
                Special offers, new dishes and events by email. You can turn this off any time.
              </span>
            </span>
            {marketing === null ? <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} /> : toggle(marketing)}
          </button>
          <p className="text-xs mt-3 h-4" style={{ color: marketingError ? "var(--red)" : "var(--text-muted)" }} role={marketingError ? "alert" : "status"}>
            {marketingError ?? (marketingState === "saving" ? "Saving…" : marketingState === "saved" ? "Saved." : "")}
          </p>
        </div>
      </div>

      {/* Sidebar */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <h3 className="font-black text-lg mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Your Data
          </h3>
          <div className="space-y-3 text-sm" style={{ color: "var(--text-muted)" }}>
            <p>• We use your details to take and deliver your orders.</p>
            <p>• We only email offers if you&apos;ve said yes above.</p>
            <p>• You can ask us to erase your account at any time.</p>
          </div>
        </div>

        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--red)" }}>
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="w-4 h-4" style={{ color: "var(--red)" }} />
            <p className="font-bold text-sm" style={{ color: "var(--black)" }}>Delete Account</p>
          </div>
          <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
            Removes your personal details and signs you out. Order records we must keep for tax are kept, but no longer
            linked to you.
          </p>

          {!confirmErase ? (
            <button
              type="button"
              onClick={() => setConfirmErase(true)}
              className="w-full px-3 py-2 rounded-lg font-bold text-sm transition-all hover:bg-red-50"
              style={{ border: "2px solid var(--red)", color: "var(--red)" }}
            >
              Delete My Account
            </button>
          ) : (
            <div className="space-y-3">
              <label htmlFor="erase-understood" className="flex items-start gap-2 cursor-pointer">
                <input id="erase-understood" type="checkbox" checked={understood} onChange={(e) => setUnderstood(e.target.checked)} className="peer sr-only" />
                <span
                  aria-hidden="true"
                  className="w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 mt-0.5 peer-focus-visible:ring-2"
                  style={{ borderColor: understood ? "var(--red)" : "var(--gray-mid)", background: understood ? "var(--red)" : "white" }}
                >
                  {understood && <Check className="w-3 h-3 text-white" />}
                </span>
                <span className="text-xs" style={{ color: "var(--black)" }}>I understand this can&apos;t be undone.</span>
              </label>
              {eraseError && <p role="alert" className="text-xs font-semibold" style={{ color: "var(--red)" }}>{eraseError}</p>}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setConfirmErase(false);
                    setUnderstood(false);
                  }}
                  className="flex-1 px-3 py-2 rounded-lg font-semibold text-sm"
                  style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
                >
                  Keep Account
                </button>
                <button
                  type="button"
                  onClick={eraseAccount}
                  disabled={!understood || erasing}
                  className="flex-1 px-3 py-2 rounded-lg font-bold text-sm text-white flex items-center justify-center gap-1 disabled:opacity-50"
                  style={{ background: "var(--red)" }}
                >
                  {erasing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Delete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
