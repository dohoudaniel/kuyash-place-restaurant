"use client";

import { useEffect, useState } from "react";
import { User, Mail, Phone, Calendar, Save, Edit2, Loader2, CheckCircle, KeyRound, ShieldCheck } from "lucide-react";
import { ApiError, api } from "@/lib/api/client";
import type { Profile } from "@/lib/api/types";
import { useAuthStore } from "@/lib/store/authStore";

const MIN_PASSWORD_LENGTH = 10;

/**
 * Personal information, from and to the account.
 *
 * The previous version showed "John Doe" to everyone, saved nothing and said
 * "Profile updated successfully!" in an alert. Its "Account Status" card —
 * 1,250 loyalty points, ₦45,600 spent, Gold tier — described a loyalty programme
 * that does not exist yet, so it is gone rather than wired to nothing.
 */
export default function ProfileSection() {
  const refreshSession = useAuthStore((state) => state.refresh);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({ full_name: "", phone: "", date_of_birth: "" });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [passwordState, setPasswordState] = useState<"idle" | "saving" | "done">("idle");
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<Profile>("/accounts/me/")
      .then((data) => {
        if (cancelled) return;
        setProfile(data);
        setFormData({ full_name: data.full_name ?? "", phone: data.phone ?? "", date_of_birth: data.date_of_birth ?? "" });
        setLoadState("ready");
      })
      .catch(() => {
        if (!cancelled) setLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const startEditing = () => {
    setSaved(false);
    setIsEditing(true);
  };

  const cancelEditing = () => {
    if (profile) setFormData({ full_name: profile.full_name ?? "", phone: profile.phone ?? "", date_of_birth: profile.date_of_birth ?? "" });
    setFieldErrors({});
    setFormError(null);
    setIsEditing(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setFieldErrors({});
    setFormError(null);
    try {
      const updated = await api<Profile>("/accounts/me/", {
        method: "PATCH",
        body: {
          full_name: formData.full_name.trim(),
          phone: formData.phone.trim(),
          date_of_birth: formData.date_of_birth || null,
        },
      });
      setProfile(updated);
      setIsEditing(false);
      setSaved(true);
      void refreshSession();
    } catch (err) {
      if (err instanceof ApiError && err.code === "validation_error") setFieldErrors(err.fieldErrors);
      else setFormError(err instanceof ApiError ? err.message : "We couldn't save your changes. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    if (passwords.next.length < MIN_PASSWORD_LENGTH) {
      setPasswordError(`Use at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (passwords.next !== passwords.confirm) {
      setPasswordError("The new passwords don't match.");
      return;
    }
    setPasswordState("saving");
    try {
      await api("/auth/password/change/", {
        method: "POST",
        body: { current_password: passwords.current, new_password: passwords.next },
      });
      setPasswords({ current: "", next: "", confirm: "" });
      setPasswordState("done");
    } catch (err) {
      setPasswordState("idle");
      setPasswordError(
        err instanceof ApiError ? err.fieldErrors.new_password ?? err.fieldErrors.current_password ?? err.message : "We couldn't change your password. Please try again."
      );
    }
  };

  if (loadState === "loading") {
    return (
      <div className="bg-white rounded-xl border p-12 flex items-center justify-center gap-2" style={{ borderColor: "var(--gray-mid)" }} role="status">
        <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading your profile…</span>
      </div>
    );
  }

  if (loadState === "error" || !profile) {
    return (
      <div className="bg-white rounded-xl border p-12 text-center" style={{ borderColor: "var(--gray-mid)" }}>
        <p role="alert" className="text-sm" style={{ color: "var(--text-muted)" }}>We couldn&apos;t load your profile. Please refresh.</p>
      </div>
    );
  }

  const inputClass = "w-full px-4 py-3 rounded-lg border font-semibold disabled:bg-gray-50";
  const errorFor = (name: string) =>
    fieldErrors[name] ? <p className="text-xs font-semibold mt-1" style={{ color: "var(--red)" }}>{fieldErrors[name]}</p> : null;

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* Profile Form */}
      <div className="lg:col-span-2 bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Personal Information
          </h2>
          {!isEditing && (
            <button
              onClick={startEditing}
              className="px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-all hover:opacity-80"
              style={{ background: "var(--gray-light)", color: "var(--black)" }}
            >
              <Edit2 className="w-4 h-4" />
              Edit
            </button>
          )}
        </div>

        {saved && !isEditing && (
          <p role="status" className="mb-4 flex items-center gap-2 text-sm font-semibold" style={{ color: "#10b981" }}>
            <CheckCircle className="w-4 h-4" />
            Your changes are saved.
          </p>
        )}

        <div className="space-y-4">
          {/* Full Name */}
          <div>
            <label htmlFor="profile-name" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              <User className="w-4 h-4 inline mr-2" />
              Full Name
            </label>
            <input
              id="profile-name"
              type="text"
              autoComplete="name"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              disabled={!isEditing}
              className={inputClass}
              style={{ borderColor: fieldErrors.full_name ? "var(--red)" : "var(--gray-mid)" }}
            />
            {errorFor("full_name")}
          </div>

          {/* Email & Phone */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="profile-email" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                <Mail className="w-4 h-4 inline mr-2" />
                Email
              </label>
              <input
                id="profile-email"
                type="email"
                value={profile.email}
                disabled
                aria-describedby="profile-email-note"
                className={inputClass}
                style={{ borderColor: "var(--gray-mid)" }}
              />
              <p id="profile-email-note" className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                {profile.is_email_verified ? "Verified. " : ""}To change your email, contact us — it must be re-verified.
              </p>
            </div>
            <div>
              <label htmlFor="profile-phone" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                <Phone className="w-4 h-4 inline mr-2" />
                Phone
              </label>
              <input
                id="profile-phone"
                type="tel"
                autoComplete="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                disabled={!isEditing}
                className={inputClass}
                style={{ borderColor: fieldErrors.phone ? "var(--red)" : "var(--gray-mid)" }}
              />
              {errorFor("phone")}
            </div>
          </div>

          {/* Birthday */}
          <div>
            <label htmlFor="profile-birthday" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              <Calendar className="w-4 h-4 inline mr-2" />
              Birthday <span className="font-normal" style={{ color: "var(--text-muted)" }}>(Optional)</span>
            </label>
            <input
              id="profile-birthday"
              type="date"
              value={formData.date_of_birth}
              onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
              disabled={!isEditing}
              className={inputClass}
              style={{ borderColor: fieldErrors.date_of_birth ? "var(--red)" : "var(--gray-mid)" }}
            />
            {errorFor("date_of_birth")}
          </div>

          {formError && <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>{formError}</p>}

          {isEditing && (
            <div className="flex gap-3 pt-4">
              <button
                onClick={cancelEditing}
                disabled={saving}
                className="px-6 py-3 rounded-lg font-bold transition-all"
                style={{ background: "var(--gray-light)", color: "var(--black)" }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: "var(--red)", color: "white" }}
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Changes
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Sidebar */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <h3 className="font-black text-lg mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Account
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Email</span>
              <span className="flex items-center gap-1 text-xs font-bold" style={{ color: profile.is_email_verified ? "#10b981" : "var(--red)" }}>
                <ShieldCheck className="w-3.5 h-3.5" />
                {profile.is_email_verified ? "Verified" : "Not verified"}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Member Since</span>
              <span className="font-bold text-sm" style={{ color: "var(--black)" }}>
                {new Date(profile.date_joined).toLocaleDateString("en-NG", { month: "long", year: "numeric" })}
              </span>
            </div>
          </div>
        </div>

        <form onSubmit={handleChangePassword} className="bg-white rounded-xl border p-6 space-y-3" style={{ borderColor: "var(--gray-mid)" }}>
          <h3 className="font-black text-lg mb-1 flex items-center gap-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            <KeyRound className="w-4 h-4" style={{ color: "var(--red)" }} />
            Change Password
          </h3>
          {(
            [
              ["current", "Current password", "current-password"],
              ["next", "New password", "new-password"],
              ["confirm", "Confirm new password", "new-password"],
            ] as const
          ).map(([key, label, autoComplete]) => (
            <div key={key}>
              <label htmlFor={`password-${key}`} className="block text-xs font-bold mb-1" style={{ color: "var(--black)" }}>{label}</label>
              <input
                id={`password-${key}`}
                type="password"
                required
                autoComplete={autoComplete}
                value={passwords[key]}
                onChange={(e) => {
                  setPasswordState("idle");
                  setPasswords({ ...passwords, [key]: e.target.value });
                }}
                className="w-full px-3 py-2 rounded-lg border text-sm"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>
          ))}
          {passwordError && <p role="alert" className="text-xs font-semibold" style={{ color: "var(--red)" }}>{passwordError}</p>}
          {passwordState === "done" && (
            <p role="status" className="text-xs font-semibold" style={{ color: "#10b981" }}>Password changed. You&apos;re still signed in here.</p>
          )}
          <button
            type="submit"
            disabled={passwordState === "saving"}
            className="w-full px-4 py-2.5 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--black)", color: "white" }}
          >
            {passwordState === "saving" && <Loader2 className="w-4 h-4 animate-spin" />}
            Update Password
          </button>
        </form>
      </div>
    </div>
  );
}
