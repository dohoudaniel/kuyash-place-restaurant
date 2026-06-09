"use client";

import { useState } from "react";
import type { MenuCategory } from "@/data/menuCategories";

interface Props {
  category: MenuCategory;
  isActive?: boolean;
  onClick?: () => void;
}

export default function MenuCategoryCard({ category, isActive = false, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-3 group cursor-pointer focus:outline-none"
    >
      <div
        className={`w-20 h-20 md:w-24 md:h-24 rounded-full flex items-center justify-center transition-all duration-200 group-hover:scale-110 group-hover:shadow-xl ${
          isActive
            ? "bg-white shadow-xl scale-105 ring-2 ring-brand-gold"
            : "bg-white/60 hover:bg-white"
        }`}
      >
        <span className="text-4xl md:text-5xl select-none">{category.emoji}</span>
      </div>
      <span
        className={`text-center text-xs md:text-sm font-semibold leading-tight transition-colors ${
          isActive ? "text-brand-gold" : "text-brand-dark group-hover:text-brand-red"
        }`}
        style={{ maxWidth: "80px" }}
      >
        {category.label}
      </span>
    </button>
  );
}
