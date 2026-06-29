"use client";

import Link from "next/link";
import { ShoppingBag } from "lucide-react";

export default function EmptyCart() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div
        className="w-24 h-24 rounded-full flex items-center justify-center mb-6"
        style={{ background: "rgba(217,4,41,0.08)" }}
      >
        <ShoppingBag className="w-12 h-12" style={{ color: "var(--red)" }} />
      </div>

      <h2
        className="font-black text-2xl sm:text-3xl mb-3 text-center"
        style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}
      >
        Your Cart is Empty
      </h2>

      <p className="text-sm sm:text-base text-center max-w-md mb-8" style={{ color: "var(--text-muted)" }}>
        Looks like you haven't added anything to your cart yet. Explore our delicious menu and find something you love!
      </p>

      <Link
        href="/#menu"
        className="flex items-center gap-2 px-8 py-3.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:scale-105 active:scale-95"
        style={{ background: "var(--red)", boxShadow: "0 8px 28px rgba(217,4,41,0.35)" }}
      >
        <ShoppingBag className="w-4 h-4" />
        Browse Menu
      </Link>
    </div>
  );
}
