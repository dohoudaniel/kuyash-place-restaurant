"use client";

import { X } from "lucide-react";

export interface MenuFiltersState {
  priceRange: [number, number];
  dietary: string[];
  rating: number;
  sortBy: "popular" | "price-low" | "price-high" | "rating";
}

interface MenuFiltersProps {
  isOpen: boolean;
  onClose: () => void;
  filters: MenuFiltersState;
  onFiltersChange: (filters: MenuFiltersState) => void;
}

const DIETARY_OPTIONS = [
  { value: "vegetarian", label: "Vegetarian" },
  { value: "vegan", label: "Vegan" },
  { value: "gluten-free", label: "Gluten-Free" },
  { value: "dairy-free", label: "Dairy-Free" },
  { value: "nut-free", label: "Nut-Free" },
  { value: "spicy", label: "Spicy" },
];

const SORT_OPTIONS = [
  { value: "popular", label: "Most Popular" },
  { value: "price-low", label: "Price: Low to High" },
  { value: "price-high", label: "Price: High to Low" },
  { value: "rating", label: "Highest Rated" },
];

export default function MenuFilters({ isOpen, onClose, filters, onFiltersChange }: MenuFiltersProps) {
  if (!isOpen) return null;

  const toggleDietary = (value: string) => {
    const newDietary = filters.dietary.includes(value)
      ? filters.dietary.filter((d) => d !== value)
      : [...filters.dietary, value];
    onFiltersChange({ ...filters, dietary: newDietary });
  };

  const resetFilters = () => {
    onFiltersChange({
      priceRange: [0, 100],
      dietary: [],
      rating: 0,
      sortBy: "popular",
    });
  };

  const activeFiltersCount =
    filters.dietary.length +
    (filters.rating > 0 ? 1 : 0) +
    (filters.priceRange[0] !== 0 || filters.priceRange[1] !== 100 ? 1 : 0);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end bg-black bg-opacity-50">
      <div
        className="w-full max-w-md h-full bg-white overflow-y-auto animate-slide-in-right"
        style={{ boxShadow: "-4px 0 20px rgba(0,0,0,0.1)" }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white z-10 px-6 py-5 border-b" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Filters
            </h2>
            <button
              onClick={onClose}
              className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          {activeFiltersCount > 0 && (
            <button
              onClick={resetFilters}
              className="text-sm font-semibold transition-colors hover:opacity-70"
              style={{ color: "var(--red)" }}
            >
              Clear all ({activeFiltersCount})
            </button>
          )}
        </div>

        <div className="p-6 space-y-8">
          {/* Sort By */}
          <div>
            <h3 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Sort By</h3>
            <div className="space-y-2">
              {SORT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => onFiltersChange({ ...filters, sortBy: option.value as any })}
                  className="w-full text-left px-4 py-3 rounded-lg transition-all text-sm font-semibold"
                  style={{
                    border: `2px solid ${filters.sortBy === option.value ? "var(--red)" : "var(--gray-mid)"}`,
                    background: filters.sortBy === option.value ? "rgba(217,4,41,0.05)" : "transparent",
                    color: filters.sortBy === option.value ? "var(--red)" : "var(--black)",
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Price Range */}
          <div>
            <h3 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>
              Price Range: ₦{filters.priceRange[0]} - ₦{filters.priceRange[1]}
            </h3>
            <div className="space-y-3">
              <input
                type="range"
                min="0"
                max="100"
                value={filters.priceRange[1]}
                onChange={(e) =>
                  onFiltersChange({ ...filters, priceRange: [filters.priceRange[0], parseInt(e.target.value)] })
                }
                className="w-full accent-red-600"
              />
              <div className="flex gap-3">
                <input
                  type="number"
                  value={filters.priceRange[0]}
                  onChange={(e) =>
                    onFiltersChange({ ...filters, priceRange: [parseInt(e.target.value) || 0, filters.priceRange[1]] })
                  }
                  className="flex-1 px-3 py-2 rounded-lg border text-sm"
                  style={{ borderColor: "var(--gray-mid)" }}
                  placeholder="Min"
                />
                <input
                  type="number"
                  value={filters.priceRange[1]}
                  onChange={(e) =>
                    onFiltersChange({ ...filters, priceRange: [filters.priceRange[0], parseInt(e.target.value) || 100] })
                  }
                  className="flex-1 px-3 py-2 rounded-lg border text-sm"
                  style={{ borderColor: "var(--gray-mid)" }}
                  placeholder="Max"
                />
              </div>
            </div>
          </div>

          {/* Dietary Preferences */}
          <div>
            <h3 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Dietary Preferences</h3>
            <div className="grid grid-cols-2 gap-2">
              {DIETARY_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => toggleDietary(option.value)}
                  className="px-3 py-2 rounded-lg text-xs font-semibold transition-all"
                  style={{
                    border: `2px solid ${filters.dietary.includes(option.value) ? "var(--red)" : "var(--gray-mid)"}`,
                    background: filters.dietary.includes(option.value) ? "rgba(217,4,41,0.05)" : "transparent",
                    color: filters.dietary.includes(option.value) ? "var(--red)" : "var(--black)",
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Minimum Rating */}
          <div>
            <h3 className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Minimum Rating</h3>
            <div className="flex gap-2">
              {[0, 3, 4, 5].map((rating) => (
                <button
                  key={rating}
                  onClick={() => onFiltersChange({ ...filters, rating })}
                  className="flex-1 flex flex-col items-center gap-1 py-3 rounded-lg transition-all"
                  style={{
                    border: `2px solid ${filters.rating === rating ? "var(--red)" : "var(--gray-mid)"}`,
                    background: filters.rating === rating ? "rgba(217,4,41,0.05)" : "transparent",
                  }}
                >
                  <span className="font-bold text-sm" style={{ color: filters.rating === rating ? "var(--red)" : "var(--black)" }}>
                    {rating === 0 ? "All" : `${rating}+`}
                  </span>
                  {rating > 0 && (
                    <div className="flex gap-0.5">
                      {[...Array(rating)].map((_, i) => (
                        <svg key={i} className="w-3 h-3" viewBox="0 0 20 20" fill="var(--red)">
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      ))}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white border-t p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <button
            onClick={onClose}
            className="w-full py-4 rounded-full font-bold text-white transition-all hover:opacity-90"
            style={{ background: "var(--red)" }}
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  );
}
