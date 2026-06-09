"use client";

import { useState } from "react";
import { MENU_CATEGORIES } from "@/data/menuCategories";

const MENU_ITEMS: Record<string, { name: string; description: string; price: string }[]> = {
  "whats-hot": [
    { name: "Signature Grill Plate", description: "Slow-cooked beef with roasted garlic & herbs", price: "$14.90" },
    { name: "Fire Chicken Combo", description: "Crispy chicken, spicy sauce, pickles & slaw", price: "$12.50" },
    { name: "Chef's Special Pasta", description: "House-made fettuccine, truffle cream, parmesan", price: "$13.90" },
  ],
  burgers: [
    { name: "Classic Smash Burger", description: "Double smash patty, American cheese, pickles", price: "$10.90" },
    { name: "BBQ Bacon Stack", description: "Beef patty, streaky bacon, BBQ sauce, onion rings", price: "$13.50" },
    { name: "Spicy Jalapeño Burger", description: "Beef patty, jalapeños, pepper jack, chipotle mayo", price: "$11.90" },
  ],
  "chicken-salad": [
    { name: "Grilled Chicken Breast", description: "Herb-marinated chicken, lemon butter, greens", price: "$12.90" },
    { name: "Caesar Salad", description: "Romaine, parmesan, house-made croutons, anchovy dressing", price: "$9.90" },
    { name: "Crispy Chicken Strips", description: "5 pieces, served with honey mustard & fries", price: "$11.50" },
  ],
  tacos: [
    { name: "Street Tacos (3 pcs)", description: "Pulled beef, pico de gallo, avocado, lime", price: "$10.90" },
    { name: "Loaded Fries", description: "Seasoned fries, cheese sauce, jalapeños, sour cream", price: "$7.50" },
    { name: "Onion Rings", description: "Beer-battered, golden crispy, ranch dip", price: "$6.90" },
  ],
  breakfast: [
    { name: "Full Breakfast Plate", description: "Eggs, bacon, sausage, toast, baked beans", price: "$11.90" },
    { name: "Pancake Stack", description: "3 fluffy pancakes, maple syrup, fresh berries", price: "$9.50" },
    { name: "Avocado Toast", description: "Sourdough, smashed avo, poached egg, chilli flakes", price: "$10.90" },
  ],
  desserts: [
    { name: "Chocolate Lava Cake", description: "Warm dark chocolate cake, vanilla ice cream", price: "$7.90" },
    { name: "Berry Cheesecake", description: "New York style, mixed berry compote", price: "$8.50" },
    { name: "Classic Milkshake", description: "Vanilla, chocolate or strawberry — your choice", price: "$6.90" },
  ],
};

export default function MenuSection() {
  const [activeSlug, setActiveSlug] = useState("burgers");

  const items = MENU_ITEMS[activeSlug] ?? [];

  return (
    <section id="menu" className="py-16 md:py-24 px-6 md:px-14" style={{ background: "var(--cream)" }}>
      {/* Heading */}
      <div className="text-center mb-10">
        <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "var(--orange)" }}>
          Our Menu
        </p>
        <h2
          className="font-black text-4xl md:text-5xl"
          style={{ fontFamily: "var(--font-playfair)", color: "var(--brown-dark)" }}
        >
          Explore Our Dishes
        </h2>
        <div className="mt-3 w-12 h-1 rounded-full mx-auto" style={{ background: "var(--orange)" }} />
      </div>

      {/* Category tabs */}
      <div className="flex items-center justify-center flex-wrap gap-3 mb-12">
        {MENU_CATEGORIES.map((cat) => {
          const isActive = cat.slug === activeSlug;
          return (
            <button
              key={cat.slug}
              onClick={() => setActiveSlug(cat.slug)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 hover:scale-105 active:scale-95"
              style={{
                background: isActive ? "var(--orange)" : "white",
                color: isActive ? "white" : "var(--brown-mid)",
                border: isActive ? "none" : "1.5px solid var(--cream-dark)",
                boxShadow: isActive ? "0 4px 14px rgba(224,91,43,0.35)" : "none",
              }}
            >
              <span aria-hidden="true">{cat.emoji}</span>
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* Menu item cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {items.map((item) => (
          <div
            key={item.name}
            className="bg-white rounded-2xl p-6 flex flex-col gap-3 transition-all duration-200 hover:shadow-lg hover:-translate-y-1 cursor-pointer"
            style={{ border: "1px solid var(--cream-dark)" }}
          >
            {/* Placeholder image area */}
            <div
              className="w-full rounded-xl flex items-center justify-center text-5xl"
              style={{ height: "120px", background: "var(--cream)" }}
              aria-hidden="true"
            >
              {MENU_CATEGORIES.find((c) => c.slug === activeSlug)?.emoji}
            </div>

            <div>
              <h3 className="font-bold text-base" style={{ color: "var(--brown-dark)" }}>
                {item.name}
              </h3>
              <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--text-muted)" }}>
                {item.description}
              </p>
            </div>

            <div className="flex items-center justify-between mt-auto pt-2">
              <span className="font-black text-lg" style={{ color: "var(--orange)" }}>
                {item.price}
              </span>
              <button
                className="px-4 py-2 rounded-full text-xs font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95"
                style={{ background: "var(--orange)" }}
              >
                Add to cart
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
