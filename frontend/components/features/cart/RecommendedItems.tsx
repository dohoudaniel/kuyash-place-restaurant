"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Sparkles, Plus, Check, Loader2 } from "lucide-react";
import { fetchFeatured } from "@/lib/api/catalog";
import { mediaUrl } from "@/lib/api/media";
import type { MenuItemSummary } from "@/lib/api/types";
import { useAddToCart } from "@/components/features/menu/useAddToCart";

interface RecommendedItemsProps {
  /** Dishes already in the cart, which are not suggested again. */
  excludeSlugs: string[];
}

/**
 * Suggestions from the kitchen's featured dishes.
 *
 * Previously "Frequently Bought Together" — a claim with no purchase data behind
 * it — showing three hardcoded dishes, dollar-figure prices, and an "Add All"
 * total summed in the browser.
 */
export default function RecommendedItems({ excludeSlugs }: RecommendedItemsProps) {
  const [featured, setFeatured] = useState<MenuItemSummary[]>([]);
  const [needsOptions, setNeedsOptions] = useState<string | null>(null);
  const { add, pending, added, error } = useAddToCart();

  useEffect(() => {
    let cancelled = false;
    fetchFeatured()
      .then((items) => {
        if (!cancelled) setFeatured(items);
      })
      .catch(() => {
        /* suggestions are optional; the section simply stays hidden */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const suggestions = featured.filter((item) => item.is_available && !excludeSlugs.includes(item.slug)).slice(0, 3);
  if (suggestions.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h3 className="font-bold text-sm mb-3 flex items-center gap-2" style={{ color: "var(--black)" }}>
        <Sparkles className="w-4 h-4" style={{ color: "var(--red)" }} />
        You Might Also Like
      </h3>

      <div className="grid grid-cols-3 gap-3 mb-4">
        {suggestions.map((item) => {
          const imageSrc = mediaUrl(item.image_url);
          return (
            <div key={item.slug} className="text-center">
              <div className="relative w-full aspect-square rounded-lg mb-2 overflow-hidden" style={{ background: "var(--cream)" }}>
                {imageSrc ? (
                  <Image src={imageSrc} alt={item.name} fill sizes="120px" className="object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-3xl">🍽️</div>
                )}
                <button
                  onClick={() => void add(item.slug, { onNeedsOptions: () => setNeedsOptions(item.slug) })}
                  disabled={pending === item.slug}
                  aria-label={`Add ${item.name} to cart`}
                  className="absolute bottom-1 right-1 w-7 h-7 rounded-full flex items-center justify-center transition-all hover:scale-110"
                  style={{ background: added === item.slug ? "var(--black)" : "var(--red)" }}
                >
                  {pending === item.slug ? (
                    <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
                  ) : added === item.slug ? (
                    <Check className="w-3.5 h-3.5 text-white" />
                  ) : (
                    <Plus className="w-3.5 h-3.5 text-white" />
                  )}
                </button>
              </div>
              <p className="text-[10px] font-semibold truncate" style={{ color: "var(--black)" }}>
                {item.name}
              </p>
              <p className="text-[10px] font-bold" style={{ color: "var(--red)" }}>
                {item.price?.display}
              </p>
              {needsOptions === item.slug && (
                <Link href={`/menu?item=${encodeURIComponent(item.slug)}`} className="block text-[10px] font-bold" style={{ color: "var(--red)" }}>
                  Choose options →
                </Link>
              )}
              {error?.slug === item.slug && (
                <p role="alert" className="text-[10px] font-semibold" style={{ color: "var(--red)" }}>{error.message}</p>
              )}
            </div>
          );
        })}
      </div>

      <Link
        href="/menu"
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-full text-xs font-bold transition-all hover:bg-gray-50"
        style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
      >
        Browse the Full Menu
      </Link>
    </div>
  );
}
