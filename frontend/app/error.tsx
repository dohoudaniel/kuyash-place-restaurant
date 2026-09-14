"use client"; // Error boundaries must be Client Components

import { useEffect } from "react";
import Link from "next/link";
import { AlertCircle, RefreshCw } from "lucide-react";

/**
 * Shown when a page throws while rendering. The message is deliberately
 * generic: in production Next.js strips server error details, and a customer
 * gains nothing from a stack trace.
 */
export default function RouteError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    // Sentry (or the browser console in development) picks this up.
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 pt-24 pb-12" style={{ background: "var(--off-white)" }}>
      <div role="alert" className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "rgba(217,4,41,0.08)" }}>
          <AlertCircle className="w-8 h-8" style={{ color: "var(--red)" }} />
        </div>
        <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Something went wrong
        </h1>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          This page couldn&apos;t load. Nothing you entered has been lost — try again, or head back to the menu.
          {error.digest && <span className="block mt-2 text-xs">Reference: {error.digest}</span>}
        </p>
        <div className="space-y-3">
          <button
            onClick={() => retry()}
            className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
            style={{ background: "var(--red)" }}
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
          <Link href="/menu" className="block w-full px-6 py-3 rounded-full text-sm font-semibold transition-all hover:bg-gray-50" style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}>
            Back to Menu
          </Link>
        </div>
      </div>
    </div>
  );
}
