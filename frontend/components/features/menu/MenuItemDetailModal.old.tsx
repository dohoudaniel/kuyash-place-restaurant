"use client";

import { useState } from "react";
import Image from "next/image";
import { X, Heart, ShoppingCart, Plus, Minus, Check } from "lucide-react";
import type { MenuItem as MenuItemType } from "@/lib/types";
import { IMAGES, type ImageKey } from "@/lib/assets/images";
import { useCartStore } from "@/lib/store/cartStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";

interface MenuItemDetailModalProps {
  item: MenuItemType;
  isOpen: boolean;
  onClose: () => void;
}

interface Customization {
  extras: string[];
  substitutions: { item: string; with: string }[];
  specialInstructions: string;
  spiceLevel: "mild" | "medium" | "hot" | "extra-hot";
  portionSize: "small" | "regular" | "large";
}

const AVAILABLE_EXTRAS = [
  { name: "Extra Cheese", price: 2.00 },
  { name: "Avocado", price: 3.50 },
  { name: "Bacon", price: 3.00 },
  { name: "Grilled Chicken", price: 5.00 },
  { name: "Extra Sauce", price: 1.00 },
  { name: "Fried Egg", price: 2.50 },
];

const DIETARY_INFO = ["Gluten-Free Option", "Vegetarian", "Spicy", "Contains Nuts"];

export default function MenuItemDetailModal({ item, isOpen, onClose }: MenuItemDetailModalProps) {
  const [quantity, setQuantity] = useState(1);
  const [customization, setCustomization] = useState<Customization>({
    extras: [],
    substitutions: [],
    specialInstructions: "",
    spiceLevel: "medium",
    portionSize: "regular",
  });
  const [added, setAdded] = useState(false);

  const { addItem } = useCartStore();
  const { addItem: addToWishlist, removeItem: removeFromWishlist, isInWishlist } = useWishlistStore();

  const imageSrc = item.imageKey ? IMAGES.menu[item.imageKey as ImageKey] : null;
  const basePrice = parseFloat(item.price.replace(/[^\d.]/g, ""));

  const extrasPrice = customization.extras.reduce((sum, extraName) => {
    const extra = AVAILABLE_EXTRAS.find(e => e.name === extraName);
    return sum + (extra?.price || 0);
  }, 0);

  const portionMultiplier = customization.portionSize === "small" ? 0.8 : customization.portionSize === "large" ? 1.3 : 1;
  const itemPrice = (basePrice + extrasPrice) * portionMultiplier;
  const totalPrice = itemPrice * quantity;

  const inWishlist = isInWishlist(item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-"));

  const handleToggleExtra = (extraName: string) => {
    setCustomization(prev => ({
      ...prev,
      extras: prev.extras.includes(extraName)
        ? prev.extras.filter(e => e !== extraName)
        : [...prev.extras, extraName],
    }));
  };

  const handleAddToCart = () => {
    addItem({
      id: item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-"),
      name: item.name,
      description: item.description,
      price: itemPrice,
      imageKey: item.imageKey,
      quantity,
    });

    setAdded(true);
    setTimeout(() => {
      setAdded(false);
      onClose();
    }, 1500);
  };

  const handleToggleWishlist = () => {
    const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.6)" }}>
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header with image */}
        <div className="relative h-64 sm:h-80" style={{ background: "var(--cream)" }}>
          {imageSrc && (
            <Image src={imageSrc} alt={item.name} fill className="object-cover" />
          )}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
            style={{ background: "rgba(255,255,255,0.95)" }}
          >
            <X className="w-5 h-5" style={{ color: "var(--black)" }} />
          </button>
          <button
            onClick={handleToggleWishlist}
            className="absolute top-4 left-4 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
            style={{ background: "rgba(255,255,255,0.95)" }}
          >
            <Heart className={`w-5 h-5 ${inWishlist ? "fill-current" : ""}`} style={{ color: "var(--red)" }} />
          </button>
        </div>

        <div className="p-6 sm:p-8">
          {/* Title and rating */}
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h2 className="font-black text-2xl sm:text-3xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {item.name}
              </h2>
              <p className="text-sm sm:text-base mb-3" style={{ color: "var(--text-muted)" }}>
                {item.description}
              </p>
              <div className="flex items-center gap-2">
                {[...Array(5)].map((_, i) => (
                  <svg key={i} className="w-4 h-4" viewBox="0 0 20 20" fill="var(--red)">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
                <span className="text-sm font-semibold ml-1" style={{ color: "var(--black)" }}>5.0</span>
                <span className="text-sm" style={{ color: "var(--text-muted)" }}>(247 reviews)</span>
              </div>
            </div>
            <div className="text-right shrink-0">
              <p className="font-black text-3xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                ₦{basePrice.toFixed(2)}
              </p>
            </div>
          </div>

          {/* Dietary info tags */}
          <div className="flex flex-wrap gap-2 mb-6">
            {DIETARY_INFO.map((info) => (
              <span
                key={info}
                className="px-3 py-1 rounded-full text-xs font-semibold"
                style={{ background: "var(--cream)", color: "var(--black)" }}
              >
                {info}
              </span>
            ))}
          </div>

          {/* Portion Size */}
          <div className="mb-6">
            <h3 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Portion Size</h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                { value: "small", label: "Small", price: basePrice * 0.8 },
                { value: "regular", label: "Regular", price: basePrice },
                { value: "large", label: "Large", price: basePrice * 1.3 },
              ].map((size) => (
                <button
                  key={size.value}
                  onClick={() => setCustomization(prev => ({ ...prev, portionSize: size.value as any }))}
                  className="p-3 rounded-lg border-2 transition-all text-center"
                  style={{
                    borderColor: customization.portionSize === size.value ? "var(--red)" : "var(--gray-mid)",
                    background: customization.portionSize === size.value ? "rgba(217,4,41,0.05)" : "transparent",
                  }}
                >
                  <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{size.label}</p>
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>₦{size.price.toFixed(2)}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Spice Level */}
          <div className="mb-6">
            <h3 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Spice Level</h3>
            <div className="grid grid-cols-4 gap-2">
              {[
                { value: "mild", label: "Mild", emoji: "🌶️" },
                { value: "medium", label: "Medium", emoji: "🌶️🌶️" },
                { value: "hot", label: "Hot", emoji: "🌶️🌶️🌶️" },
                { value: "extra-hot", label: "Extra Hot", emoji: "🌶️🌶️🌶️🔥" },
              ].map((level) => (
                <button
                  key={level.value}
                  onClick={() => setCustomization(prev => ({ ...prev, spiceLevel: level.value as any }))}
                  className="p-2 rounded-lg border-2 transition-all text-center"
                  style={{
                    borderColor: customization.spiceLevel === level.value ? "var(--red)" : "var(--gray-mid)",
                    background: customization.spiceLevel === level.value ? "rgba(217,4,41,0.05)" : "transparent",
                  }}
                >
                  <p className="text-lg mb-1">{level.emoji}</p>
                  <p className="text-xs font-semibold" style={{ color: "var(--black)" }}>{level.label}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Extras */}
          <div className="mb-6">
            <h3 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Add Extras</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {AVAILABLE_EXTRAS.map((extra) => (
                <button
                  key={extra.name}
                  onClick={() => handleToggleExtra(extra.name)}
                  className="flex items-center justify-between p-3 rounded-lg border-2 transition-all"
                  style={{
                    borderColor: customization.extras.includes(extra.name) ? "var(--red)" : "var(--gray-mid)",
                    background: customization.extras.includes(extra.name) ? "rgba(217,4,41,0.05)" : "transparent",
                  }}
                >
                  <span className="text-sm font-semibold" style={{ color: "var(--black)" }}>{extra.name}</span>
                  <span className="text-sm font-bold" style={{ color: "var(--red)" }}>+₦{extra.price.toFixed(2)}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Special Instructions */}
          <div className="mb-6">
            <h3 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Special Instructions</h3>
            <textarea
              value={customization.specialInstructions}
              onChange={(e) => setCustomization(prev => ({ ...prev, specialInstructions: e.target.value }))}
              placeholder="Any special requests? (e.g., no onions, extra sauce on the side)"
              className="w-full p-3 rounded-lg border-2 text-sm resize-none"
              style={{ borderColor: "var(--gray-mid)" }}
              rows={3}
            />
          </div>

          {/* Quantity and Add to Cart */}
          <div className="flex items-center gap-4 pt-6 border-t" style={{ borderColor: "var(--gray-mid)" }}>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:opacity-80"
                style={{ background: "var(--gray-mid)" }}
                disabled={quantity <= 1}
              >
                <Minus className="w-4 h-4" style={{ color: "var(--black)" }} />
              </button>
              <span className="font-bold text-lg w-8 text-center" style={{ color: "var(--black)" }}>{quantity}</span>
              <button
                onClick={() => setQuantity(quantity + 1)}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                <Plus className="w-4 h-4 text-white" />
              </button>
            </div>

            <button
              onClick={handleAddToCart}
              className="flex-1 flex items-center justify-center gap-2 py-4 rounded-full font-bold text-white transition-all hover:opacity-90"
              style={{ background: added ? "var(--black)" : "var(--red)" }}
            >
              {added ? (
                <>
                  <Check className="w-5 h-5" />
                  Added to Cart!
                </>
              ) : (
                <>
                  <ShoppingCart className="w-5 h-5" />
                  Add ₦{totalPrice.toFixed(2)} to Cart
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
