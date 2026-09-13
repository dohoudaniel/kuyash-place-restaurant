"use client";

import { Search, SlidersHorizontal, Grid3x3, List, LayoutGrid, ArrowUpDown } from "lucide-react";
import { SORT_OPTIONS, countActiveFilters, type MenuFilters, type SortOption, type ViewMode } from "./filters";

interface MenuFiltersBarProps {
  filters: MenuFilters;
  onFiltersChange: (filters: MenuFilters) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onShowFilters: () => void;
  resultsCount: number;
  isLoading?: boolean;
}

export default function MenuFiltersBar({
  filters,
  onFiltersChange,
  viewMode,
  onViewModeChange,
  onShowFilters,
  resultsCount,
  isLoading = false,
}: MenuFiltersBarProps) {
  const activeFiltersCount = countActiveFilters(filters);

  return (
    <div className="sticky top-20 sm:top-24 z-20 bg-white rounded-xl border p-4 mb-6 shadow-sm" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="flex-1 flex items-center gap-3 px-4 py-2.5 rounded-lg border" style={{ borderColor: "var(--gray-mid)" }}>
          <Search className="w-5 h-5" style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => onFiltersChange({ ...filters, search: e.target.value })}
            placeholder="Search dishes, ingredients..."
            aria-label="Search the menu"
            className="flex-1 outline-none text-sm"
            style={{ color: "var(--black)" }}
          />
        </div>

        {/* Sort Dropdown */}
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg border" style={{ borderColor: "var(--gray-mid)" }}>
          <ArrowUpDown className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
          <select
            value={filters.sortBy}
            onChange={(e) => onFiltersChange({ ...filters, sortBy: e.target.value as SortOption })}
            aria-label="Sort dishes"
            className="outline-none text-sm font-semibold cursor-pointer bg-transparent"
            style={{ color: "var(--black)" }}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Advanced Filters Button */}
        <button
          onClick={onShowFilters}
          className="relative flex items-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-sm transition-all hover:opacity-80"
          style={{
            border: `2px solid ${activeFiltersCount > 0 ? "var(--red)" : "var(--gray-mid)"}`,
            background: activeFiltersCount > 0 ? "rgba(217,4,41,0.05)" : "white",
            color: activeFiltersCount > 0 ? "var(--red)" : "var(--black)",
          }}
        >
          <SlidersHorizontal className="w-4 h-4" />
          <span className="hidden sm:inline">Filters</span>
          {activeFiltersCount > 0 && (
            <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ background: "var(--red)" }}>
              {activeFiltersCount}
            </span>
          )}
        </button>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 p-1 rounded-lg" style={{ border: "1px solid var(--gray-mid)" }}>
          <button
            onClick={() => onViewModeChange("grid")}
            className="p-2 rounded transition-all"
            style={{ background: viewMode === "grid" ? "var(--red)" : "transparent" }}
            title="Grid View"
            aria-label="Grid view"
          >
            <Grid3x3 className="w-4 h-4" style={{ color: viewMode === "grid" ? "white" : "var(--text-muted)" }} />
          </button>
          <button
            onClick={() => onViewModeChange("list")}
            className="p-2 rounded transition-all"
            style={{ background: viewMode === "list" ? "var(--red)" : "transparent" }}
            title="List View"
            aria-label="List view"
          >
            <List className="w-4 h-4" style={{ color: viewMode === "list" ? "white" : "var(--text-muted)" }} />
          </button>
          <button
            onClick={() => onViewModeChange("compact")}
            className="p-2 rounded transition-all"
            style={{ background: viewMode === "compact" ? "var(--red)" : "transparent" }}
            title="Compact View"
            aria-label="Compact view"
          >
            <LayoutGrid className="w-4 h-4" style={{ color: viewMode === "compact" ? "white" : "var(--text-muted)" }} />
          </button>
        </div>
      </div>

      {/* Results Count */}
      <div className="mt-3 text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
        {isLoading ? "Updating…" : `Showing ${resultsCount} ${resultsCount === 1 ? "item" : "items"}`}
        {filters.search && ` for "${filters.search}"`}
      </div>
    </div>
  );
}
