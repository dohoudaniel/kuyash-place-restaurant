"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { MenuCategory } from "@/lib/types";

interface MenuCategoriesScrollProps {
  categories: MenuCategory[];
  activeCategory: string;
  onCategoryChange: (category: string) => void;
}

export default function MenuCategoriesScroll({
  categories,
  activeCategory,
  onCategoryChange,
}: MenuCategoriesScrollProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showLeftArrow, setShowLeftArrow] = useState(false);
  const [showRightArrow, setShowRightArrow] = useState(true);

  const allCategories = [
    { label: "All Items", slug: "all", emoji: "🍽️" },
    ...categories,
  ];

  const checkScroll = () => {
    if (scrollRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
      setShowLeftArrow(scrollLeft > 0);
      setShowRightArrow(scrollLeft < scrollWidth - clientWidth - 10);
    }
  };

  useEffect(() => {
    checkScroll();
    const current = scrollRef.current;
    if (current) {
      current.addEventListener("scroll", checkScroll);
      return () => current.removeEventListener("scroll", checkScroll);
    }
  }, []);

  const scroll = (direction: "left" | "right") => {
    if (scrollRef.current) {
      const scrollAmount = 300;
      scrollRef.current.scrollBy({
        left: direction === "left" ? -scrollAmount : scrollAmount,
        behavior: "smooth",
      });
    }
  };

  return (
    <div className="relative mb-6">
      {/* Left Arrow */}
      {showLeftArrow && (
        <button
          onClick={() => scroll("left")}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition-all hover:scale-110"
          style={{ background: "white", border: "2px solid var(--gray-mid)" }}
        >
          <ChevronLeft className="w-5 h-5" style={{ color: "var(--black)" }} />
        </button>
      )}

      {/* Categories Scroll */}
      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto scrollbar-hide scroll-smooth px-12"
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        {allCategories.map((category) => (
          <button
            key={category.slug}
            onClick={() => onCategoryChange(category.slug)}
            className="shrink-0 px-6 py-3 rounded-full font-bold text-sm transition-all hover:scale-105 whitespace-nowrap"
            style={{
              background: activeCategory === category.slug ? "var(--red)" : "white",
              color: activeCategory === category.slug ? "white" : "var(--black)",
              border: `2px solid ${activeCategory === category.slug ? "var(--red)" : "var(--gray-mid)"}`,
            }}
          >
            <span className="mr-2">{category.emoji}</span>
            {category.label}
          </button>
        ))}
      </div>

      {/* Right Arrow */}
      {showRightArrow && (
        <button
          onClick={() => scroll("right")}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition-all hover:scale-110"
          style={{ background: "white", border: "2px solid var(--gray-mid)" }}
        >
          <ChevronRight className="w-5 h-5" style={{ color: "var(--black)" }} />
        </button>
      )}
    </div>
  );
}
