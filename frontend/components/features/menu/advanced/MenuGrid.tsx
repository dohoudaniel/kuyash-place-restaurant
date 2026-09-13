"use client";

import Image from "next/image";
import { ShoppingCart, Heart, Check, Plus, Loader2 } from "lucide-react";
import type { MenuItemSummary } from "@/lib/api/types";
import { mediaUrl } from "@/lib/api/media";
import { useWishlistStore } from "@/lib/store/wishlistStore";
import StarRating from "../StarRating";
import { useAddToCart } from "../useAddToCart";
import type { ViewMode } from "./filters";

interface MenuGridProps {
  items: MenuItemSummary[];
  viewMode: ViewMode;
  selectedItems: Set<string>;
  onSelectItem: (slug: string) => void;
  /** Opens the item dialog (the page keeps it in the URL so it can be shared). */
  onOpenItem: (slug: string) => void;
}

export default function MenuGrid({ items, viewMode, selectedItems, onSelectItem, onOpenItem }: MenuGridProps) {
  const { add, pending, added, error } = useAddToCart();
  const { addItem: addToWishlist, removeItem: removeFromWishlist, isInWishlist } = useWishlistStore();

  const handleAddToCart = (item: MenuItemSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    void add(item.slug, { onNeedsOptions: () => onOpenItem(item.slug) });
  };

  const handleToggleWishlist = (item: MenuItemSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    if (isInWishlist(item.slug)) {
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

  const handleSelectItem = (item: MenuItemSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectItem(item.slug);
  };

  const openOnEnter = (slug: string) => (e: React.KeyboardEvent) => {
    if (e.key === "Enter") onOpenItem(slug);
  };

  const addIcon = (item: MenuItemSummary, size: string) =>
    pending === item.slug ? (
      <Loader2 className={`${size} animate-spin`} />
    ) : added === item.slug ? (
      <Check className={size} />
    ) : null;

  if (viewMode === "list") {
    return (
      <div className="space-y-3">
        {items.map((item) => {
          const isSelected = selectedItems.has(item.slug);
          const isAdded = added === item.slug;
          const inWishlist = isInWishlist(item.slug);
          const imageSrc = mediaUrl(item.image_url);

          return (
            <div
              key={item.slug}
              onClick={() => onOpenItem(item.slug)}
              onKeyDown={openOnEnter(item.slug)}
              tabIndex={0}
              className="bg-white rounded-xl p-4 flex items-center gap-4 transition-all hover:shadow-lg cursor-pointer"
              style={{ border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}` }}
            >
              {/* Checkbox */}
              <button
                onClick={(e) => handleSelectItem(item, e)}
                role="checkbox"
                aria-checked={isSelected}
                aria-label={`Select ${item.name}`}
                className="w-6 h-6 rounded border-2 flex items-center justify-center shrink-0 transition-all"
                style={{
                  borderColor: isSelected ? "var(--red)" : "var(--gray-mid)",
                  background: isSelected ? "var(--red)" : "white",
                }}
              >
                {isSelected && <Check className="w-4 h-4 text-white" />}
              </button>

              {/* Image */}
              <div className="relative w-24 h-24 rounded-lg overflow-hidden shrink-0" style={{ background: "var(--cream)" }}>
                {imageSrc ? (
                  <Image src={imageSrc} alt={item.name} fill sizes="96px" className="object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-3xl">🍽️</div>
                )}
              </div>

              {/* Details */}
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-base truncate" style={{ color: "var(--black)" }}>
                  {item.name}
                </h3>
                <p className="text-sm mt-1 line-clamp-2" style={{ color: "var(--text-muted)" }}>
                  {item.description}
                </p>
                <div className="mt-2">
                  <StarRating rating={item.average_rating} count={item.review_count} starClassName="w-3 h-3" />
                </div>
                {error?.slug === item.slug && (
                  <p role="alert" className="text-xs font-semibold mt-1" style={{ color: "var(--red)" }}>{error.message}</p>
                )}
              </div>

              {/* Price */}
              <div className="text-right shrink-0">
                <p className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                  {item.price?.display}
                </p>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => handleToggleWishlist(item, e)}
                    aria-label={inWishlist ? `Remove ${item.name} from wishlist` : `Save ${item.name} to wishlist`}
                    aria-pressed={inWishlist}
                    className="w-9 h-9 rounded-full flex items-center justify-center transition-all hover:bg-red-50"
                    style={{ border: "2px solid var(--gray-mid)" }}
                  >
                    <Heart className={`w-4 h-4 ${inWishlist ? "fill-current" : ""}`} style={{ color: "var(--red)" }} />
                  </button>
                  <button
                    onClick={(e) => handleAddToCart(item, e)}
                    disabled={pending === item.slug || !item.is_available}
                    className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold text-white transition-all hover:opacity-90 disabled:opacity-50"
                    style={{ background: isAdded ? "var(--black)" : "var(--red)" }}
                  >
                    {addIcon(item, "w-4 h-4") ?? <ShoppingCart className="w-4 h-4" />}
                    {!item.is_available ? "Unavailable" : isAdded ? "Added" : "Add"}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`grid gap-6 ${
      viewMode === "grid"
        ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
        : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
    }`}>
      {items.map((item) => {
        const isSelected = selectedItems.has(item.slug);
        const isAdded = added === item.slug;
        const inWishlist = isInWishlist(item.slug);
        const imageSrc = mediaUrl(item.image_url);

        return (
          <div
            key={item.slug}
            onClick={() => onOpenItem(item.slug)}
            onKeyDown={openOnEnter(item.slug)}
            tabIndex={0}
            className="bg-white rounded-xl overflow-hidden transition-all hover:shadow-lg cursor-pointer"
            style={{ border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}` }}
          >
            {/* Image */}
            <div className="relative w-full h-40" style={{ background: "var(--cream)" }}>
              {imageSrc ? (
                <Image src={imageSrc} alt={item.name} fill sizes="(max-width: 640px) 50vw, 25vw" className="object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-5xl">🍽️</div>
              )}

              {/* Selection Checkbox */}
              <button
                onClick={(e) => handleSelectItem(item, e)}
                role="checkbox"
                aria-checked={isSelected}
                aria-label={`Select ${item.name}`}
                className="absolute top-3 left-3 w-6 h-6 rounded border-2 flex items-center justify-center transition-all"
                style={{
                  borderColor: isSelected ? "var(--red)" : "white",
                  background: isSelected ? "var(--red)" : "rgba(255,255,255,0.9)",
                }}
              >
                {isSelected && <Check className="w-4 h-4 text-white" />}
              </button>

              {/* Wishlist */}
              <button
                onClick={(e) => handleToggleWishlist(item, e)}
                aria-label={inWishlist ? `Remove ${item.name} from wishlist` : `Save ${item.name} to wishlist`}
                aria-pressed={inWishlist}
                className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{ background: "rgba(255,255,255,0.95)" }}
              >
                <Heart className={`w-4 h-4 ${inWishlist ? "fill-current" : ""}`} style={{ color: "var(--red)" }} />
              </button>
            </div>

            {/* Content */}
            <div className="p-4">
              <h3 className="font-bold text-sm truncate mb-1" style={{ color: "var(--black)" }}>
                {item.name}
              </h3>
              {viewMode === "grid" && (
                <p className="text-xs line-clamp-2 mb-2" style={{ color: "var(--text-muted)" }}>
                  {item.description}
                </p>
              )}

              <div className="flex items-center justify-between mt-2">
                <span className="font-black text-lg" style={{ color: "var(--red)" }}>
                  {item.price?.display}
                </span>
                <button
                  onClick={(e) => handleAddToCart(item, e)}
                  disabled={pending === item.slug || !item.is_available}
                  aria-label={`Add ${item.name} to cart`}
                  className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110 disabled:opacity-50"
                  style={{ background: isAdded ? "var(--black)" : "var(--red)" }}
                >
                  {addIcon(item, "w-4 h-4 text-white") ?? <Plus className="w-4 h-4 text-white" />}
                </button>
              </div>
              {error?.slug === item.slug && (
                <p role="alert" className="text-xs font-semibold mt-2" style={{ color: "var(--red)" }}>{error.message}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
