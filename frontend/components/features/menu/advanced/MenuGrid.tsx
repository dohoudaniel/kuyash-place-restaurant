"use client";

import { useState } from "react";
import Image from "next/image";
import { ShoppingCart, Heart, Check, Info, Plus } from "lucide-react";
import { useCartStore } from "@/lib/store/cartStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";
import type { MenuItem } from "@/lib/types";
import type { ViewMode } from "@/app/menu/page";
import MenuItemDetailModal from "../MenuItemDetailModal";

interface MenuGridProps {
  items: MenuItem[];
  viewMode: ViewMode;
  selectedItems: Set<string>;
  onSelectItem: (itemId: string) => void;
}

export default function MenuGrid({ items, viewMode, selectedItems, onSelectItem }: MenuGridProps) {
  const { addItem } = useCartStore();
  const { addItem: addToWishlist, removeItem: removeFromWishlist, isInWishlist } = useWishlistStore();
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set());
  const [detailItem, setDetailItem] = useState<MenuItem | null>(null);

  const handleAddToCart = (item: MenuItem, e: React.MouseEvent) => {
    e.stopPropagation();
    const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");
    const price = parseFloat(item.price.replace(/[^\d.]/g, ""));

    addItem({
      id: itemId,
      name: item.name,
      description: item.description,
      price,
      imageKey: item.imageKey,
    });

    setAddedItems(prev => new Set(prev).add(itemId));
    setTimeout(() => {
      setAddedItems(prev => {
        const newSet = new Set(prev);
        newSet.delete(itemId);
        return newSet;
      });
    }, 2000);
  };

  const handleToggleWishlist = (item: MenuItem, e: React.MouseEvent) => {
    e.stopPropagation();
    const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");

    if (isInWishlist(itemId)) {
      removeFromWishlist(itemId);
    } else {
      addToWishlist({
        id: itemId,
        name: item.name,
        description: item.description,
        price: item.price,
        imageKey: item.imageKey,
      });
    }
  };

  const handleSelectItem = (item: MenuItem, e: React.MouseEvent) => {
    e.stopPropagation();
    const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");
    onSelectItem(itemId);
  };

  if (viewMode === "list") {
    return (
      <>
        <div className="space-y-3">
          {items.map((item) => {
            const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");
            const isSelected = selectedItems.has(itemId);
            const isAdded = addedItems.has(itemId);
            const inWishlist = isInWishlist(itemId);

            return (
              <div
                key={itemId}
                onClick={() => setDetailItem(item)}
                className="bg-white rounded-xl p-4 flex items-center gap-4 transition-all hover:shadow-lg cursor-pointer"
                style={{ border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}` }}
              >
                {/* Checkbox */}
                <button
                  onClick={(e) => handleSelectItem(item, e)}
                  className="w-6 h-6 rounded border-2 flex items-center justify-center shrink-0 transition-all"
                  style={{
                    borderColor: isSelected ? "var(--red)" : "var(--gray-mid)",
                    background: isSelected ? "var(--red)" : "white",
                  }}
                >
                  {isSelected && <Check className="w-4 h-4 text-white" />}
                </button>

                {/* Image */}
                <div className="w-24 h-24 rounded-lg overflow-hidden shrink-0" style={{ background: "var(--cream)" }}>
                  {item.imageKey ? (
                    <Image
                      src={`/assets/menu/${item.imageKey}.png`}
                      alt={item.name}
                      width={96}
                      height={96}
                      className="w-full h-full object-cover"
                    />
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
                  <div className="flex items-center gap-1 mt-2">
                    {[...Array(5)].map((_, i) => (
                      <svg key={i} className="w-3 h-3" viewBox="0 0 20 20" fill="var(--red)">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    ))}
                    <span className="text-xs ml-1" style={{ color: "var(--text-muted)" }}>5.0 (247)</span>
                  </div>
                </div>

                {/* Price */}
                <div className="text-right shrink-0">
                  <p className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                    {item.price}
                  </p>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => handleToggleWishlist(item, e)}
                      className="w-9 h-9 rounded-full flex items-center justify-center transition-all hover:bg-red-50"
                      style={{ border: "2px solid var(--gray-mid)" }}
                    >
                      <Heart className={`w-4 h-4 ${inWishlist ? "fill-current" : ""}`} style={{ color: "var(--red)" }} />
                    </button>
                    <button
                      onClick={(e) => handleAddToCart(item, e)}
                      className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
                      style={{ background: isAdded ? "var(--black)" : "var(--red)" }}
                    >
                      {isAdded ? <Check className="w-4 h-4" /> : <ShoppingCart className="w-4 h-4" />}
                      {isAdded ? "Added" : "Add"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {detailItem && (
          <MenuItemDetailModal
            item={detailItem}
            isOpen={true}
            onClose={() => setDetailItem(null)}
          />
        )}
      </>
    );
  }

  // Grid and Compact views would go here (similar structure to existing MenuItem component)
  return (
    <div className={`grid gap-6 ${
      viewMode === "grid"
        ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
        : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
    }`}>
      {items.map((item) => {
        const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");
        const isSelected = selectedItems.has(itemId);
        const isAdded = addedItems.has(itemId);
        const inWishlist = isInWishlist(itemId);

        return (
          <div
            key={itemId}
            onClick={() => setDetailItem(item)}
            className="bg-white rounded-xl overflow-hidden transition-all hover:shadow-lg cursor-pointer"
            style={{ border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}` }}
          >
            {/* Image */}
            <div className="relative w-full h-40" style={{ background: "var(--cream)" }}>
              {item.imageKey ? (
                <Image
                  src={`/assets/menu/${item.imageKey}.png`}
                  alt={item.name}
                  fill
                  className="object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-5xl">🍽️</div>
              )}

              {/* Selection Checkbox */}
              <button
                onClick={(e) => handleSelectItem(item, e)}
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
                  {item.price}
                </span>
                <button
                  onClick={(e) => handleAddToCart(item, e)}
                  className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
                  style={{ background: isAdded ? "var(--black)" : "var(--red)" }}
                >
                  {isAdded ? <Check className="w-4 h-4 text-white" /> : <Plus className="w-4 h-4 text-white" />}
                </button>
              </div>
            </div>
          </div>
        );
      })}

      {detailItem && (
        <MenuItemDetailModal
          item={detailItem}
          isOpen={true}
          onClose={() => setDetailItem(null)}
        />
      )}
    </div>
  );
}
