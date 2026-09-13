"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ShoppingCart, X, Loader2 } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { mediaUrl } from "@/lib/api/media";
import { useCartStore } from "@/lib/store/cartStore";
import { useWishlistStore, type WishlistItem } from "@/lib/store/wishlistStore";

export default function SavedForLater() {
  const { items, removeItem } = useWishlistStore();
  const addItem = useCartStore((state) => state.addItem);
  const [pending, setPending] = useState<string | null>(null);
  const [problem, setProblem] = useState<{ slug: string; needsOptions: boolean; message: string } | null>(null);

  if (items.length === 0) return null;

  const handleMoveToCart = async (item: WishlistItem) => {
    setPending(item.slug);
    setProblem(null);
    try {
      // Re-priced by the server: the saved price is only what it cost then.
      await addItem({ menu_item: item.slug });
      removeItem(item.slug);
    } catch (err) {
      const needsOptions = err instanceof ApiError && err.code === "cart_invalid";
      setProblem({
        slug: item.slug,
        needsOptions,
        message: needsOptions ? "Choose options" : err instanceof ApiError ? err.message : "Couldn't add",
      });
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h3 className="font-bold text-sm mb-4 flex items-center gap-2" style={{ color: "var(--black)" }}>
        <span>Saved for Later</span>
        <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--cream)", color: "var(--text-muted)" }}>
          {items.length}
        </span>
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {items.slice(0, 6).map((item) => {
          const imageSrc = mediaUrl(item.imageUrl);
          return (
            <div
              key={item.slug}
              className="relative group rounded-lg overflow-hidden border transition-all hover:shadow-lg"
              style={{ borderColor: "var(--gray-mid)" }}
            >
              <div className="relative w-full h-24 sm:h-28" style={{ background: "var(--cream)" }}>
                {imageSrc ? (
                  <Image src={imageSrc} alt={item.name} fill sizes="(max-width: 640px) 50vw, 33vw" className="object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-2xl">🍽️</div>
                )}

                {/* Remove button */}
                <button
                  onClick={() => removeItem(item.slug)}
                  aria-label={`Remove ${item.name} from saved items`}
                  className="absolute top-1 right-1 w-6 h-6 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all"
                  style={{ background: "rgba(255,255,255,0.95)" }}
                >
                  <X className="w-3 h-3" style={{ color: "var(--red)" }} />
                </button>
              </div>

              <div className="p-2">
                <h4 className="font-semibold text-xs truncate" style={{ color: "var(--black)" }}>
                  {item.name}
                </h4>
                <div className="flex items-center justify-between mt-1">
                  <span className="font-bold text-xs" style={{ color: "var(--red)" }}>
                    {item.price}
                  </span>
                  <button
                    onClick={() => handleMoveToCart(item)}
                    disabled={pending === item.slug}
                    className="p-1 rounded transition-all hover:bg-red-50"
                    title="Move to cart"
                    aria-label={`Move ${item.name} to cart`}
                  >
                    {pending === item.slug ? (
                      <Loader2 className="w-3 h-3 animate-spin" style={{ color: "var(--red)" }} />
                    ) : (
                      <ShoppingCart className="w-3 h-3" style={{ color: "var(--red)" }} />
                    )}
                  </button>
                </div>
                {problem?.slug === item.slug && (
                  problem.needsOptions ? (
                    <Link href={`/menu?item=${encodeURIComponent(item.slug)}`} className="block text-[10px] font-bold mt-1" style={{ color: "var(--red)" }}>
                      Choose options →
                    </Link>
                  ) : (
                    <p role="alert" className="text-[10px] font-semibold mt-1" style={{ color: "var(--red)" }}>{problem.message}</p>
                  )
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
