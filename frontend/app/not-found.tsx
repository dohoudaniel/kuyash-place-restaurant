import Link from "next/link";
import { SearchX } from "lucide-react";

/** Any unmatched URL, and any page that calls `notFound()`. */
export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 pt-24 pb-12" style={{ background: "var(--off-white)" }}>
      <div className="bg-white rounded-xl border p-8 max-w-md w-full text-center" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "var(--gray-light)" }}>
          <SearchX className="w-8 h-8" style={{ color: "var(--text-muted)" }} />
        </div>
        <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          We couldn&apos;t find that page
        </h1>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          The link may be old, or the page may have moved.
        </p>
        <div className="space-y-3">
          <Link href="/menu" className="block w-full px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90" style={{ background: "var(--red)" }}>
            See the Menu
          </Link>
          <Link href="/" className="block w-full px-6 py-3 rounded-full text-sm font-semibold transition-all hover:bg-gray-50" style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}>
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
