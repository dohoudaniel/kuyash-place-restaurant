"use client";

import { useState } from "react";
import Image from "next/image";
import { ShoppingCart, Check, Heart } from "lucide-react";
import type { MenuItem as MenuItemType, MenuCategory } from "@/lib/types";
import { IMAGES, type ImageKey } from "@/lib/assets/images";
import { useCartStore } from "@/lib/store/cartStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";
import MenuItemDetailModal from "./MenuItemDetailModal";

interface MenuItemProps {
  item: MenuItemType;
  activeCategory?: MenuCategory;
}

export default function MenuItem({ item, activeCategory }: MenuItemProps) {
  const [added, setAdded] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const { addItem } = useCartStore();
  const { addItem: addToWishlist, removeItem: removeFromWishlist, isInWishlist } = useWishlistStore();

  const imageSrc = item.imageKey
    ? IMAGES.menu[item.imageKey as ImageKey]
    : null;

  const priceValue = parseFloat(item.price.replace(/[^\d.]/g, ""));
  const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");
  const inWishlist = isInWishlist(itemId);

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    addItem({
      id: itemId,
      name: item.name,
      description: item.description,
      price: priceValue,
      imageKey: item.imageKey,
    });

    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  const handleToggleWishlist = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (inWishlist) {
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

  return (
    <>
      <div
        onClick={() => setShowDetailModal(true)}
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
              {activeCategory?.emoji}
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
          <div className="flex items-center gap-1">
            {[...Array(5)].map((_, i) => (
              <svg key={i} className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="var(--red)">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ))}
            <span className="text-xs ml-1" style={{ color: "var(--text-muted)" }}>5.0</span>
          </div>

          <div className="flex items-center justify-between mt-auto pt-1">
            <span className="font-black text-lg" style={{ color: "var(--red)" }}>
              {item.price}
            </span>
            <button
              onClick={handleAddToCart}
              className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95"
              style={{ background: added ? "var(--black)" : "var(--red)" }}
            >
              {added ? (
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
        </div>
      </div>

      <MenuItemDetailModal
        item={item}
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
      />
    </>
  );
}
