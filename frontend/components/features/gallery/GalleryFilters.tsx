"use client";

import { Utensils, Home, PartyPopper, Users, Sparkles, Grid } from "lucide-react";
import type { GalleryCategory } from "@/app/gallery/page";

interface GalleryFiltersProps {
  selectedCategory: GalleryCategory;
  onSelectCategory: (category: GalleryCategory) => void;
  counts: Record<GalleryCategory, number>;
}

export default function GalleryFilters({ selectedCategory, onSelectCategory, counts }: GalleryFiltersProps) {
  const categories: { id: GalleryCategory; label: string; icon: any; color: string }[] = [
    { id: "all", label: "All Photos", icon: Grid, color: "var(--red)" },
    { id: "food", label: "Food", icon: Utensils, color: "#f59e0b" },
    { id: "interior", label: "Interior", icon: Home, color: "#3b82f6" },
    { id: "events", label: "Events", icon: PartyPopper, color: "#ec4899" },
    { id: "team", label: "Team", icon: Users, color: "#10b981" },
    { id: "ambiance", label: "Ambiance", icon: Sparkles, color: "#8b5cf6" },
  ];

  return (
    <div className="mb-6">
      <div className="flex gap-3 overflow-x-auto pb-3">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const isActive = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => onSelectCategory(cat.id)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg font-bold text-sm whitespace-nowrap transition-all hover:shadow-md min-w-fit"
              style={{
                background: isActive ? cat.color : "white",
                color: isActive ? "white" : "var(--black)",
                border: `2px solid ${isActive ? cat.color : "var(--gray-mid)"}`,
              }}
            >
              <Icon className="w-4 h-4" />
              {cat.label}
              <span
                className="px-2 py-0.5 rounded-full text-xs font-black"
                style={{
                  background: isActive ? "rgba(255,255,255,0.3)" : "var(--gray-light)",
                  color: isActive ? "white" : "var(--text-muted)",
                }}
              >
                {counts[cat.id]}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
