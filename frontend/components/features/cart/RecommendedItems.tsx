"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";

export default function RecommendedItems() {
  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h3 className="font-bold text-sm mb-3 flex items-center gap-2" style={{ color: "var(--black)" }}>
        <Sparkles className="w-4 h-4" style={{ color: "var(--red)" }} />
        Frequently Bought Together
      </h3>

      <div className="grid grid-cols-3 gap-3 mb-4">
        {["burger-1", "fries-1", "drink-1"].map((key, idx) => (
          <div key={key} className="text-center">
            <div className="w-full aspect-square rounded-lg mb-2" style={{ background: "var(--cream)" }}>
              <div className="w-full h-full flex items-center justify-center text-3xl">
                {idx === 0 ? "🍔" : idx === 1 ? "🍟" : "🥤"}
              </div>
            </div>
            <p className="text-[10px] font-semibold truncate" style={{ color: "var(--black)" }}>
              {idx === 0 ? "Classic Burger" : idx === 1 ? "Crispy Fries" : "Soft Drink"}
            </p>
            <p className="text-[10px] font-bold" style={{ color: "var(--red)" }}>
              ₦{idx === 0 ? "14.90" : idx === 1 ? "6.90" : "3.50"}
            </p>
          </div>
        ))}
      </div>

      <Link
        href="/#menu"
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-full text-xs font-bold transition-all hover:bg-gray-50"
        style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
      >
        Add All to Cart • ₦25.30
      </Link>
    </div>
  );
}
