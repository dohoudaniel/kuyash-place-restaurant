"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import type { EscalationInput } from "@/lib/api/chat";

interface ChatEscalationFormProps {
  /** The signed-in customer's name; their account supplies name and email. */
  signedInName: string | null;
  onSubmit: (input: EscalationInput) => Promise<void>;
  onCancel: () => void;
}

const fieldClass = "w-full text-sm px-3.5 py-2 rounded-full outline-none transition-all";
const fieldStyle = { background: "#F3F3F3", color: "var(--black)", border: "1px solid transparent" };

/** Hand the conversation to a person. It arrives in the team's ticket queue with the transcript. */
export default function ChatEscalationForm({ signedInName, onSubmit, onCancel }: ChatEscalationFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrors({});
    setError(null);
    try {
      await onSubmit(signedInName ? { message } : { name, email, message });
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) {
        setErrors(err.fieldErrors);
      } else {
        setError(err instanceof ApiError ? err.message : "Couldn't reach our team. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="px-3 py-3 space-y-2" style={{ borderTop: "1px solid #F0F0F0" }}>
      <p className="text-xs font-semibold" style={{ color: "var(--black)" }}>
        {signedInName ? `We'll reply to your account email, ${signedInName.split(" ")[0]}.` : "Our team will reply by email."}
      </p>
      {!signedInName && (
        <>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            aria-label="Your name"
            aria-invalid={Boolean(errors.name)}
            required
            maxLength={150}
            className={fieldClass}
            style={fieldStyle}
          />
          {errors.name && <p className="text-xs" style={{ color: "var(--red)" }}>{errors.name}</p>}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email address"
            aria-label="Email address"
            aria-invalid={Boolean(errors.email)}
            required
            className={fieldClass}
            style={fieldStyle}
          />
          {errors.email && <p className="text-xs" style={{ color: "var(--red)" }}>{errors.email}</p>}
        </>
      )}
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Anything to add? (optional)"
        aria-label="Message for our team"
        rows={2}
        maxLength={2000}
        className="w-full text-sm px-3.5 py-2 rounded-xl outline-none resize-none"
        style={fieldStyle}
      />
      {(errors.message || error) && (
        <p role="alert" className="text-xs" style={{ color: "var(--red)" }}>{errors.message || error}</p>
      )}
      <div className="flex gap-2">
        <button type="button" onClick={onCancel} className="flex-1 py-2 rounded-full text-xs font-bold" style={{ background: "#F3F3F3", color: "var(--black)" }}>
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="flex-1 py-2 rounded-full text-xs font-bold text-white transition-all hover:opacity-90 disabled:opacity-40"
          style={{ background: "var(--red)" }}
        >
          {submitting ? "Sending…" : "Send to our team"}
        </button>
      </div>
    </form>
  );
}
