"use client";

import { useState } from "react";
import { Send, CheckCircle } from "lucide-react";

export default function ContactForm() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    subject: "",
    message: "",
    reason: "general" as "general" | "reservation" | "catering" | "feedback" | "partnership",
  });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  };

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Send Us a Message
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Reason for Contact */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            I'm reaching out about
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {[
              { value: "general", label: "General" },
              { value: "reservation", label: "Reservation" },
              { value: "catering", label: "Catering" },
              { value: "feedback", label: "Feedback" },
              { value: "partnership", label: "Partnership" },
            ].map((reason) => (
              <button
                key={reason.value}
                type="button"
                onClick={() => setFormData({ ...formData, reason: reason.value as any })}
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
        </div>

        {/* Name & Email */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Your Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="John Doe"
              required
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Email Address *
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="john@example.com"
              required
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        {/* Phone & Subject */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Phone Number
            </label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="+234 123 456 7890"
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Subject
            </label>
            <input
              type="text"
              value={formData.subject}
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              placeholder="How can we help?"
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        {/* Message */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Your Message *
          </label>
          <textarea
            value={formData.message}
            onChange={(e) => setFormData({ ...formData, message: e.target.value })}
            placeholder="Tell us more about your inquiry..."
            rows={6}
            required
            className="w-full px-4 py-3 rounded-lg border font-semibold resize-none"
            style={{ borderColor: "var(--gray-mid)" }}
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="w-full px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90"
          style={{ background: "var(--red)", color: "white" }}
        >
          {submitted ? (
            <>
              <CheckCircle className="w-5 h-5" />
              Message Sent!
            </>
          ) : (
            <>
              <Send className="w-5 h-5" />
              Send Message
            </>
          )}
        </button>
      </form>
    </div>
  );
}
