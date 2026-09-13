"use client";

import { useState } from "react";
import { Send, CheckCircle, Loader2 } from "lucide-react";
import { ApiError, api } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/authStore";

type Reason = "general" | "reservation" | "catering" | "feedback" | "partnership";

const REASONS: { value: Reason; label: string }[] = [
  { value: "general", label: "General" },
  { value: "reservation", label: "Reservation" },
  { value: "catering", label: "Catering" },
  { value: "feedback", label: "Feedback" },
  { value: "partnership", label: "Partnership" },
];

/**
 * The contact form, delivered. Previously it flashed "Message Sent!" for three
 * seconds and discarded the message; now it opens a ticket the team answers.
 */
export default function ContactForm() {
  const user = useAuthStore((state) => state.user);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    subject: "",
    message: "",
    reason: "general" as Reason,
    // A field real visitors never see. Bots fill in every field they find.
    website: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [reference, setReference] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const name = formData.name || user?.full_name || "";
  const email = formData.email || user?.email || "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFieldErrors({});
    setFormError(null);
    try {
      const ack = await api<{ reference: string; detail: string }>("/support/contact/", {
        method: "POST",
        body: { ...formData, name: name.trim(), email: email.trim(), phone: formData.phone.trim() },
      });
      setReference(ack.reference || "");
      setFormData((current) => ({ ...current, subject: "", message: "" }));
    } catch (err) {
      if (err instanceof ApiError && err.code === "validation_error") setFieldErrors(err.fieldErrors);
      else if (err instanceof ApiError && err.code === "rate_limited") setFormError("You've sent a few messages already. Please wait a little before sending another.");
      else setFormError(err instanceof ApiError ? err.message : "We couldn't send your message. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass = "w-full px-4 py-3 rounded-lg border font-semibold";
  const borderFor = (field: string) => ({ borderColor: fieldErrors[field] ? "var(--red)" : "var(--gray-mid)" });
  const errorFor = (field: string) =>
    fieldErrors[field] ? <p className="text-xs font-semibold mt-1" style={{ color: "var(--red)" }}>{fieldErrors[field]}</p> : null;

  if (reference !== null) {
    return (
      <div className="bg-white rounded-xl border p-6 sm:p-8 text-center" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "#10b98115" }}>
          <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />
        </div>
        <h2 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Message sent
        </h2>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          {reference ? <>Your reference is <strong style={{ color: "var(--black)" }}>{reference}</strong>. </> : null}
          We&apos;ve emailed you a copy and will reply to {email}.
        </p>
        <button
          onClick={() => setReference(null)}
          className="px-6 py-3 rounded-lg font-bold text-sm"
          style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
        >
          Send Another Message
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Send Us a Message
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Reason for Contact */}
        <fieldset>
          <legend className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            I&apos;m reaching out about
          </legend>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2" role="radiogroup">
            {REASONS.map((reason) => (
              <button
                key={reason.value}
                type="button"
                role="radio"
                aria-checked={formData.reason === reason.value}
                onClick={() => setFormData({ ...formData, reason: reason.value })}
                className="px-3 py-2 rounded-lg text-xs font-bold transition-all"
                style={{
                  background: formData.reason === reason.value ? "var(--red)" : "var(--gray-light)",
                  color: formData.reason === reason.value ? "white" : "var(--black)",
                }}
              >
                {reason.label}
              </button>
            ))}
          </div>
        </fieldset>

        {/* Honeypot — hidden from people and from assistive technology. */}
        <div aria-hidden="true" className="absolute -left-[10000px] w-px h-px overflow-hidden">
          <label htmlFor="contact-website">Leave this empty</label>
          <input
            id="contact-website"
            type="text"
            tabIndex={-1}
            autoComplete="off"
            value={formData.website}
            onChange={(e) => setFormData({ ...formData, website: e.target.value })}
          />
        </div>

        {/* Name & Email */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="contact-name" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Your Name *
            </label>
            <input id="contact-name" type="text" autoComplete="name" value={name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="John Doe" required className={inputClass} style={borderFor("name")} />
            {errorFor("name")}
          </div>
          <div>
            <label htmlFor="contact-email" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Email Address *
            </label>
            <input id="contact-email" type="email" autoComplete="email" value={email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} placeholder="john@example.com" required className={inputClass} style={borderFor("email")} />
            {errorFor("email")}
          </div>
        </div>

        {/* Phone & Subject */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="contact-phone" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Phone Number
            </label>
            <input id="contact-phone" type="tel" autoComplete="tel" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} placeholder="+234 123 456 7890" className={inputClass} style={borderFor("phone")} />
            {errorFor("phone")}
          </div>
          <div>
            <label htmlFor="contact-subject" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Subject
            </label>
            <input id="contact-subject" type="text" maxLength={200} value={formData.subject} onChange={(e) => setFormData({ ...formData, subject: e.target.value })} placeholder="How can we help?" className={inputClass} style={borderFor("subject")} />
            {errorFor("subject")}
          </div>
        </div>

        {/* Message */}
        <div>
          <label htmlFor="contact-message" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Your Message *
          </label>
          <textarea id="contact-message" value={formData.message} onChange={(e) => setFormData({ ...formData, message: e.target.value })} placeholder="Tell us more about your inquiry..." rows={6} maxLength={5000} required className={`${inputClass} resize-none`} style={borderFor("message")} />
          {errorFor("message")}
        </div>

        {formError && <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>{formError}</p>}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={submitting}
          className="w-full px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--red)", color: "white" }}
        >
          {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          {submitting ? "Sending..." : "Send Message"}
        </button>
      </form>
    </div>
  );
}
