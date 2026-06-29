"use client";

import { useState } from "react";
import { MENU_CATEGORIES, MENU_ITEMS } from "@/lib/data/menu";
import MenuCategories from "./MenuCategories";
import MenuGrid from "./MenuGrid";

export default function MenuSection() {
  const [activeSlug, setActiveSlug] = useState("burgers");

  const items = MENU_ITEMS[activeSlug] ?? [];
  const activeCategory = MENU_CATEGORIES.find((c) => c.slug === activeSlug);

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
      <MenuCategories
        categories={MENU_CATEGORIES}
        activeSlug={activeSlug}
        onCategoryChange={setActiveSlug}
      />

      {/* Menu item cards */}
      <MenuGrid items={items} activeCategory={activeCategory} />
    </section>
  );
}
