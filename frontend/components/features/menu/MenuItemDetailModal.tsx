"use client";

import { useState } from "react";
import { X, Plus, Minus, ShoppingCart, Heart, Share2, AlertCircle } from "lucide-react";
import type { MenuItem } from "@/lib/types";
import { useCartStore } from "@/lib/store/cartStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";

interface MenuItemDetailModalProps {
  item: MenuItem;
  isOpen: boolean;
  onClose: () => void;
}

interface Customization {
  id: string;
  name: string;
  options: { id: string; name: string; price: number }[];
  required: boolean;
  multiSelect: boolean;
}

const MOCK_CUSTOMIZATIONS: Customization[] = [
  {
    id: "spice",
    name: "Spice Level",
    required: true,
    multiSelect: false,
    options: [
      { id: "mild", name: "Mild", price: 0 },
      { id: "medium", name: "Medium", price: 0 },
      { id: "hot", name: "Hot", price: 0 },
      { id: "extra-hot", name: "Extra Hot", price: 0 },
    ],
  },
  {
    id: "size",
    name: "Portion Size",
    required: true,
    multiSelect: false,
    options: [
      { id: "regular", name: "Regular", price: 0 },
      { id: "large", name: "Large (+₦500)", price: 500 },
      { id: "family", name: "Family Size (+₦1000)", price: 1000 },
    ],
  },
  {
    id: "extras",
    name: "Add-ons",
    required: false,
    multiSelect: true,
    options: [
      { id: "extra-meat", name: "Extra Meat", price: 300 },
      { id: "extra-cheese", name: "Extra Cheese", price: 200 },
      { id: "avocado", name: "Avocado", price: 150 },
      { id: "plantain", name: "Fried Plantain", price: 100 },
    ],
  },
];

export default function MenuItemDetailModal({ item, isOpen, onClose }: MenuItemDetailModalProps) {
  const [quantity, setQuantity] = useState(1);
  const [selectedOptions, setSelectedOptions] = useState<Record<string, string[]>>({});
  const [specialInstructions, setSpecialInstructions] = useState("");
  const { addItem } = useCartStore();
  const { addItem: addToWishlist, isInWishlist } = useWishlistStore();

  if (!isOpen) return null;

  const basePrice = parseFloat(item.price.replace("₦", "").replace(",", ""));

  // Calculate additional price from customizations
  const additionalPrice = Object.entries(selectedOptions).reduce((total, [customizationId, optionIds]) => {
    const customization = MOCK_CUSTOMIZATIONS.find(c => c.id === customizationId);
    if (!customization) return total;

    return total + optionIds.reduce((sum, optionId) => {
      const option = customization.options.find(o => o.id === optionId);
      return sum + (option?.price || 0);
    }, 0);
  }, 0);

  const totalPrice = (basePrice + additionalPrice) * quantity;

  const handleOptionToggle = (customizationId: string, optionId: string, multiSelect: boolean) => {
    setSelectedOptions(prev => {
      const current = prev[customizationId] || [];

      if (multiSelect) {
        // Toggle in array
        if (current.includes(optionId)) {
          return { ...prev, [customizationId]: current.filter(id => id !== optionId) };
        } else {
          return { ...prev, [customizationId]: [...current, optionId] };
        }
      } else {
        // Replace with single selection
        return { ...prev, [customizationId]: [optionId] };
      }
    });
  };

  const getItemId = () => item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");

  const canAddToCart = () => {
    // Check if all required customizations are selected
    return MOCK_CUSTOMIZATIONS.filter(c => c.required).every(c =>
      selectedOptions[c.id] && selectedOptions[c.id].length > 0
    );
  };

  const handleAddToCart = () => {
    if (!canAddToCart()) {
      alert("Please select all required options");
      return;
    }

    addItem({
      id: getItemId(),
      name: item.name,
      description: item.description,
      price: basePrice + additionalPrice,
      quantity,
      imageKey: item.imageKey,
    });

    alert(`Added ${quantity}x ${item.name} to cart!`);
    onClose();
  };

  const handleAddToWishlist = () => {
    addToWishlist({
      id: getItemId(),
      name: item.name,
      description: item.description,
      price: item.price,
      imageKey: item.imageKey,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.7)" }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Image */}
        <div className="relative h-64 sm:h-80" style={{ background: "var(--gray-light)" }}>
          <div className="w-full h-full flex items-center justify-center">
            <ShoppingCart className="w-24 h-24" style={{ color: "var(--text-muted)" }} />
          </div>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
            style={{ background: "rgba(255,255,255,0.9)" }}
          >
            <X className="w-6 h-6" style={{ color: "var(--black)" }} />
          </button>

          {/* Actions */}
          <div className="absolute top-4 left-4 flex gap-2">
            <button
              onClick={handleAddToWishlist}
              className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
              style={{ background: "rgba(255,255,255,0.9)" }}
            >
              <Heart
                className={`w-5 h-5 ${isInWishlist(getItemId()) ? "fill-red-500 text-red-500" : ""}`}
                style={{ color: isInWishlist(getItemId()) ? "var(--red)" : "var(--black)" }}
              />
            </button>
            <button
              onClick={() => alert("Share functionality")}
              className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
              style={{ background: "rgba(255,255,255,0.9)" }}
            >
              <Share2 className="w-5 h-5" style={{ color: "var(--black)" }} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 sm:p-8">
          {/* Title & Description */}
          <div className="mb-6">
            <h2 className="font-black text-2xl sm:text-3xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              {item.name}
            </h2>
            <p className="text-sm sm:text-base mb-3" style={{ color: "var(--text-muted)" }}>
              {item.description}
            </p>
            <p className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
              {item.price}
            </p>
          </div>

          {/* Allergen Warning */}
          <div className="mb-6 p-4 rounded-lg flex items-start gap-3" style={{ background: "#fef3c715", border: "1px solid #fef3c7" }}>
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "#f59e0b" }} />
            <div>
              <p className="font-bold text-sm mb-1" style={{ color: "var(--black)" }}>Allergen Information</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Contains: Gluten, Dairy. May contain traces of nuts.
              </p>
            </div>
          </div>

          {/* Customizations */}
          <div className="space-y-6 mb-6">
            {MOCK_CUSTOMIZATIONS.map((customization) => (
              <div key={customization.id}>
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="font-black text-lg" style={{ color: "var(--black)" }}>
                    {customization.name}
                  </h3>
                  {customization.required && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-bold text-white" style={{ background: "var(--red)" }}>
                      Required
                    </span>
                  )}
                </div>

                <div className="grid sm:grid-cols-2 gap-2">
                  {customization.options.map((option) => {
                    const isSelected = selectedOptions[customization.id]?.includes(option.id);
                    return (
                      <button
                        key={option.id}
                        onClick={() => handleOptionToggle(customization.id, option.id, customization.multiSelect)}
                        className="p-3 rounded-lg text-left transition-all"
                        style={{
                          background: isSelected ? "var(--red)08" : "var(--gray-light)",
                          border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}`,
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-sm" style={{ color: "var(--black)" }}>
                            {option.name}
                          </span>
                          {option.price > 0 && (
                            <span className="text-xs font-bold" style={{ color: "var(--red)" }}>
                              +₦{option.price}
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Special Instructions */}
          <div className="mb-6">
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Special Instructions (Optional)
            </label>
            <textarea
              value={specialInstructions}
              onChange={(e) => setSpecialInstructions(e.target.value)}
              placeholder="Any special requests? (e.g., less spicy, extra sauce)"
              rows={3}
              className="w-full px-4 py-3 rounded-lg border font-semibold resize-none"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>

          {/* Quantity & Add to Cart */}
          <div className="flex items-center gap-4">
            {/* Quantity */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:opacity-80"
                style={{ background: "var(--gray-light)", color: "var(--black)" }}
              >
                <Minus className="w-4 h-4" />
              </button>
              <span className="font-black text-xl w-8 text-center" style={{ color: "var(--black)" }}>
                {quantity}
              </span>
              <button
                onClick={() => setQuantity(quantity + 1)}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:opacity-80"
                style={{ background: "var(--red)", color: "white" }}
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            {/* Add to Cart */}
            <button
              onClick={handleAddToCart}
              disabled={!canAddToCart()}
              className="flex-1 px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-40"
              style={{ background: "var(--red)", color: "white" }}
            >
              <ShoppingCart className="w-5 h-5" />
              Add to Cart • ₦{totalPrice.toLocaleString()}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
