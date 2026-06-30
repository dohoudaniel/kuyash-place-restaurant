"use client";

import { ShoppingCart, Trash2, Heart } from "lucide-react";
import { useWishlistStore } from "@/lib/store/wishlistStore";
import { useCartStore } from "@/lib/store/cartStore";
import Image from "next/image";
import { useState } from "react";
import Link from "next/link";

export default function WishlistPage() {
  const { items, removeItem, clearWishlist, getTotalItems } = useWishlistStore();
  const { addItem: addToCart } = useCartStore();
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set());

  const handleAddToCart = (item: typeof items[0]) => {
    const priceValue = parseFloat(item.price.replace(/[^\d.]/g, ""));

    addToCart({
      id: item.id,
      name: item.name,
      description: item.description,
      price: priceValue,
      imageKey: item.imageKey,
    });

    setAddedItems(prev => new Set(prev).add(item.id));
    setTimeout(() => {
      setAddedItems(prev => {
        const newSet = new Set(prev);
        newSet.delete(item.id);
        return newSet;
      });
    }, 2000);
  };

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-16">
        <div className="container-custom">
          {/* Page Header */}
          <div className="mb-8 sm:mb-12 flex items-center justify-between">
            <div>
              <h1 className="font-black text-3xl sm:text-4xl lg:text-5xl mb-2"
                style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                My Wishlist
              </h1>
              <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
                {getTotalItems()} {getTotalItems() === 1 ? "item" : "items"} saved for later
              </p>
            </div>
            {items.length > 0 && (
              <button
                onClick={clearWishlist}
                className="px-4 py-2 rounded-full text-sm font-semibold transition-all hover:bg-red-50"
                style={{ border: "2px solid var(--red)", color: "var(--red)" }}
              >
                Clear All
              </button>
            )}
          </div>

          {items.length === 0 ? (
            /* Empty State */
            <div className="flex flex-col items-center justify-center py-16 sm:py-24">
              <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-full flex items-center justify-center mb-6"
                style={{ background: "rgba(217,4,41,0.1)" }}>
                <Heart className="w-12 h-12 sm:w-16 sm:h-16" style={{ color: "var(--red)" }} />
              </div>
              <h2 className="font-black text-2xl sm:text-3xl mb-3" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                Your wishlist is empty
              </h2>
              <p className="text-sm sm:text-base mb-8 text-center max-w-md" style={{ color: "var(--text-muted)" }}>
                Save your favorite dishes to your wishlist and order them later
              </p>
              <Link
                href="/#menu"
                className="px-8 py-3 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Browse Menu
              </Link>
            </div>
          ) : (
            /* Wishlist Grid */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="bg-white rounded-2xl overflow-hidden flex flex-col transition-all duration-200 hover:shadow-lg"
                  style={{ border: "1px solid var(--cream-dark)" }}
                >
                  {/* Image */}
                  <div className="relative w-full" style={{ height: "160px", background: "var(--cream)" }}>
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

                    {/* Remove button */}
                    <button
                      onClick={() => removeItem(item.id)}
                      className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
                      style={{ background: "rgba(255,255,255,0.95)" }}
                    >
                      <Trash2 className="w-4 h-4" style={{ color: "var(--red)" }} />
                    </button>
                  </div>

                  {/* Content */}
                  <div className="p-5 flex flex-col gap-3 flex-1">
                    <div>
                      <h3 className="font-bold text-base" style={{ color: "var(--brown-dark)" }}>
                        {item.name}
                      </h3>
                      <p className="text-xs mt-1 leading-relaxed line-clamp-2" style={{ color: "var(--text-muted)" }}>
                        {item.description}
                      </p>
                    </div>

                    <div className="flex items-center justify-between mt-auto pt-2">
                      <span className="font-black text-lg" style={{ color: "var(--red)" }}>
                        {item.price}
                      </span>
                      <button
                        onClick={() => handleAddToCart(item)}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold text-white transition-all duration-200 hover:opacity-90"
                        style={{ background: addedItems.has(item.id) ? "var(--black)" : "var(--red)" }}
                      >
                        <ShoppingCart className="w-3.5 h-3.5" />
                        {addedItems.has(item.id) ? "Added" : "Add to cart"}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
