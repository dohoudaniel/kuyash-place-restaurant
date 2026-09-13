"use client";

import { GraduationCap, ChefHat, Cake, Image, Briefcase, Apple, type LucideIcon } from "lucide-react";
import type { CourseLevel, CourseType } from "@/lib/api/types";

export type LevelFilter = "all" | CourseLevel;
export type TypeFilter = "all" | CourseType;

interface CourseFiltersProps {
  selectedCategory: LevelFilter;
  selectedType: TypeFilter;
  onSelectCategory: (category: LevelFilter) => void;
  onSelectType: (type: TypeFilter) => void;
}

export default function CourseFilters({
  selectedCategory,
  selectedType,
  onSelectCategory,
  onSelectType,
}: CourseFiltersProps) {
  const categories: { id: LevelFilter; label: string }[] = [
    { id: "all", label: "All Levels" },
    { id: "beginner", label: "Beginner" },
    { id: "intermediate", label: "Intermediate" },
    { id: "advanced", label: "Advanced" },
    { id: "masterclass", label: "Masterclass" },
  ];

  const types: { id: TypeFilter; label: string; icon: LucideIcon; color: string }[] = [
    { id: "all", label: "All Types", icon: GraduationCap, color: "var(--red)" },
    { id: "cooking", label: "Cooking", icon: ChefHat, color: "#f59e0b" },
    { id: "baking", label: "Baking", icon: Cake, color: "#ec4899" },
    { id: "plating", label: "Plating", icon: Image, color: "#8b5cf6" },
    { id: "business", label: "Business", icon: Briefcase, color: "#3b82f6" },
    { id: "nutrition", label: "Nutrition", icon: Apple, color: "#10b981" },
  ];

  return (
    <div className="mb-6 space-y-3">
      {/* Level Filter */}
      <div>
        <p className="text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
          Level
        </p>
        <div className="flex gap-2 overflow-x-auto pb-2">
          {categories.map((cat) => {
            const isActive = selectedCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => onSelectCategory(cat.id)}
                aria-pressed={isActive}
                className="px-4 py-2 rounded-lg font-bold text-sm whitespace-nowrap transition-all hover:shadow-md"
                style={{
                  background: isActive ? "var(--red)" : "white",
                  color: isActive ? "white" : "var(--black)",
                  border: `2px solid ${isActive ? "var(--red)" : "var(--gray-mid)"}`,
                }}
              >
                {cat.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Type Filter */}
      <div>
        <p className="text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
          Course Type
        </p>
        <div className="flex gap-2 overflow-x-auto pb-2">
          {types.map((type) => {
            const Icon = type.icon;
            const isActive = selectedType === type.id;
            return (
              <button
                key={type.id}
                onClick={() => onSelectType(type.id)}
                aria-pressed={isActive}
                className="px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 whitespace-nowrap transition-all hover:shadow-md"
                style={{
                  background: isActive ? type.color : "white",
                  color: isActive ? "white" : "var(--black)",
                  border: `2px solid ${isActive ? type.color : "var(--gray-mid)"}`,
                }}
              >
                <Icon className="w-4 h-4" />
                {type.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
