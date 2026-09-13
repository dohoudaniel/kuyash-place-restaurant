"use client";

import { useState } from "react";
import Image from "next/image";
import { ShoppingCart, Check, Heart, Loader2 } from "lucide-react";
import type { Category, MenuItemSummary } from "@/lib/api/types";
import { mediaUrl } from "@/lib/api/media";
import { useWishlistStore } from "@/lib/store/wishlistStore";
import MenuItemDetailModal from "./MenuItemDetailModal";
import StarRating from "./StarRating";
import { useAddToCart } from "./useAddToCart";

interface MenuItemProps {
  item: MenuItemSummary;
  activeCategory?: Category;
}

export default function MenuItem({ item, activeCategory }: MenuItemProps) {
  const [showDetailModal, setShowDetailModal] = useState(false);
  const { add, pending, added, error } = useAddToCart();
  const { addItem: addToWishlist, removeItem: removeFromWishlist, isInWishlist } = useWishlistStore();

  const imageSrc = mediaUrl(item.image_url);
  const inWishlist = isInWishlist(item.slug);
  const isAdding = pending === item.slug;
  const isAdded = added === item.slug;

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    void add(item.slug, { onNeedsOptions: () => setShowDetailModal(true) });
  };

  const handleToggleWishlist = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (inWishlist) {
      removeFromWishlist(item.slug);
    } else {
      addToWishlist({
        slug: item.slug,
        name: item.name,
        description: item.description ?? "",
        price: item.price?.display ?? "",
        imageUrl: item.image_url,
      });
    }
  };

  return (
    <>
      <div
        onClick={() => setShowDetailModal(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter") setShowDetailModal(true);
        }}
        tabIndex={0}
        className="bg-white rounded-2xl overflow-hidden flex flex-col transition-all duration-200 hover:shadow-lg hover:-translate-y-1 cursor-pointer"
        style={{ border: "1px solid var(--cream-dark)" }}
      >
        {/* Image area */}
        <div
          className="relative w-full flex items-center justify-center"
          style={{ height: "160px", background: "var(--cream)" }}
        >
          {/* Wishlist button */}
          <button
            onClick={handleToggleWishlist}
            aria-label={inWishlist ? `Remove ${item.name} from wishlist` : `Save ${item.name} to wishlist`}
            aria-pressed={inWishlist}
            className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110 z-10"
            style={{ background: "rgba(255,255,255,0.95)" }}
          >
            <Heart className={`w-4 h-4 ${inWishlist ? "fill-current" : ""}`} style={{ color: "var(--red)" }} />
          </button>

          {imageSrc ? (
            <Image
              src={imageSrc}
              alt={item.name}
              fill
              className="object-cover"
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
            />
          ) : (
            <span className="text-5xl" aria-hidden="true">
              {activeCategory?.emoji || "🍽️"}
            </span>
          )}
        </div>

        {/* Content */}
        <div className="p-5 flex flex-col gap-3 flex-1">
          <div>
            <h3 className="font-bold text-base" style={{ color: "var(--brown-dark)" }}>
              {item.name}
            </h3>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--text-muted)" }}>
              {item.description}
            </p>
          </div>

          {/* Star rating */}
          <StarRating rating={item.average_rating} count={item.review_count} />

          <div className="flex items-center justify-between mt-auto pt-1">
            <span className="flex items-baseline gap-2">
              <span className="font-black text-lg" style={{ color: "var(--red)" }}>
                {item.price?.display}
              </span>
              {item.compare_at_price && (
                <span className="text-xs line-through" style={{ color: "var(--text-muted)" }}>
                  {item.compare_at_price.display}
                </span>
              )}
            </span>
            <button
              onClick={handleAddToCart}
              disabled={isAdding || !item.is_available}
              className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
              style={{ background: isAdded ? "var(--black)" : "var(--red)" }}
            >
              {!item.is_available ? (
                "Unavailable"
              ) : isAdding ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Adding
                </>
              ) : isAdded ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  Added
                </>
              ) : (
                <>
                  <ShoppingCart className="w-3.5 h-3.5" />
                  Add to cart
                </>
              )}
            </button>
          </div>

          {error?.slug === item.slug && (
            <p role="alert" className="text-xs font-semibold" style={{ color: "var(--red)" }}>
              {error.message}
            </p>
          )}
        </div>
      </div>

      <MenuItemDetailModal
        slug={item.slug}
        summary={item}
        fallbackEmoji={activeCategory?.emoji}
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
      />
    </>
  );
}
