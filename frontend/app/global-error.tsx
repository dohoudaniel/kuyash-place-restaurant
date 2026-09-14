"use client"; // Error boundaries must be Client Components

import { useEffect } from "react";
import "./globals.css";

/**
 * The last line of defence: the root layout itself failed, so this renders
 * without the navbar, footer or fonts. Kept plain on purpose.
 */
export default function GlobalError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen flex items-center justify-center px-4" style={{ background: "var(--off-white)" }}>
        <div role="alert" className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <h1 className="font-black text-2xl mb-2" style={{ color: "var(--black)" }}>Kuyash Place is having trouble</h1>
          <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
            Please try again in a moment.
            {error.digest && <span className="block mt-2 text-xs">Reference: {error.digest}</span>}
          </p>
          <button
            onClick={() => retry()}
            className="w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
            style={{ background: "var(--red)" }}
          >
            Try Again
          </button>
        </div>
      </body>
    </html>
  );
}
