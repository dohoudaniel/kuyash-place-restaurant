"use client";

import { useState } from "react";

export default function FooterNewsletter() {
  const [email, setEmail] = useState("");

  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.18em] mb-5" style={{ color: "var(--red)" }}>
        Newsletter
      </p>
      <p className="text-sm mb-4" style={{ color: "rgba(255,255,255,0.55)" }}>
        Get exclusive offers, new menu drops and special events delivered to your inbox.
      </p>
      <form
        onSubmit={(e) => { e.preventDefault(); setEmail(""); }}
        className="flex flex-col gap-3"
      >
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Your email address"
          required
          className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all duration-200"
          style={{
            background: "rgba(255,255,255,0.07)",
            border: "1px solid rgba(255,255,255,0.12)",
            color: "white",
          }}
        />
        <button
          type="submit"
          className="w-full py-3 rounded-xl text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-[1.02] active:scale-95"
          style={{ background: "var(--red)" }}
        >
          Subscribe
        </button>
      </form>
    </div>
  );
}
