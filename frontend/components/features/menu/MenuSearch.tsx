"use client";

import { Search, X, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

interface MenuSearchProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onFilterToggle: () => void;
  activeFiltersCount: number;
}

export default function MenuSearch({ searchQuery, onSearchChange, onFilterToggle, activeFiltersCount }: MenuSearchProps) {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <div className="flex gap-3">
      {/* Search Input */}
      <div
        className="flex-1 flex items-center gap-3 px-4 py-3 rounded-xl transition-all"
        style={{
          border: `2px solid ${isFocused ? "var(--red)" : "var(--gray-mid)"}`,
          background: "white",
        }}
      >
        <Search className="w-5 h-5 shrink-0" style={{ color: "var(--text-muted)" }} />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Search for dishes, ingredients..."
          className="flex-1 outline-none text-sm"
          style={{ color: "var(--black)" }}
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange("")}
            className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
          >
            <X className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
          </button>
        )}
      </div>

      {/* Filter Button */}
      <button
        onClick={onFilterToggle}
        className="relative shrink-0 flex items-center gap-2 px-5 py-3 rounded-xl font-semibold text-sm transition-all hover:opacity-90"
        style={{
          border: `2px solid ${activeFiltersCount > 0 ? "var(--red)" : "var(--gray-mid)"}`,
          background: activeFiltersCount > 0 ? "rgba(217,4,41,0.05)" : "white",
          color: activeFiltersCount > 0 ? "var(--red)" : "var(--black)",
        }}
      >
        <SlidersHorizontal className="w-4 h-4" />
        <span className="hidden sm:inline">Filters</span>
        {activeFiltersCount > 0 && (
          <span
            className="absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white"
            style={{ background: "var(--red)" }}
          >
            {activeFiltersCount}
          </span>
        )}
      </button>
    </div>
  );
}
