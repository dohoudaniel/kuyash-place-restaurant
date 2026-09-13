"use client";

import type { Category } from "@/lib/api/types";

interface MenuCategoriesProps {
  categories: Category[];
  activeSlug: string;
  onCategoryChange: (slug: string) => void;
}

export default function MenuCategories({ categories, activeSlug, onCategoryChange }: MenuCategoriesProps) {
  return (
    <div className="flex items-center justify-center flex-wrap gap-3 mb-12">
      {categories.map((cat) => {
        const isActive = cat.slug === activeSlug;
        return (
          <button
            key={cat.slug}
            onClick={() => onCategoryChange(cat.slug)}
            aria-pressed={isActive}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 hover:scale-105 active:scale-95"
            style={{
              background: isActive ? "var(--orange)" : "white",
              color: isActive ? "white" : "var(--brown-mid)",
              border: isActive ? "none" : "1.5px solid var(--cream-dark)",
              boxShadow: isActive ? "0 4px 14px rgba(224,91,43,0.35)" : "none",
            }}
          >
            <span aria-hidden="true">{cat.emoji}</span>
            {cat.name}
          </button>
        );
      })}
    </div>
  );
}
