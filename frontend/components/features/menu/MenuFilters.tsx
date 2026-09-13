"use client";

import { X } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Dialog, DialogClose, DialogOverlay, DialogPortal, DialogTitle } from "@/components/ui/dialog";
import type { DietaryTag } from "@/lib/api/types";
import {
  DEFAULT_FILTERS,
  PRICE_BANDS,
  SORT_OPTIONS,
  countActiveFilters,
  type MenuFilters as MenuFiltersState,
} from "./advanced/filters";

interface MenuFiltersProps {
  isOpen: boolean;
  onClose: () => void;
  filters: MenuFiltersState;
  onFiltersChange: (filters: MenuFiltersState) => void;
  /** The server's filter vocabulary — not a hardcoded list the backend may not recognise. */
  dietaryTags: DietaryTag[];
  resultsCount: number;
}

const STAR_PATH =
  "M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z";

/**
 * The advanced filters panel for /menu.
 *
 * The page previously opened an empty overlay when "Filters" was pressed; this
 * panel existed but was never mounted. Filters apply as they are chosen.
 */
export default function MenuFilters({ isOpen, onClose, filters, onFiltersChange, dietaryTags, resultsCount }: MenuFiltersProps) {
  const toggleDietary = (value: string) => {
    const newDietary = filters.dietary.includes(value)
      ? filters.dietary.filter((d) => d !== value)
      : [...filters.dietary, value];
    onFiltersChange({ ...filters, dietary: newDietary });
  };

  const resetFilters = () => {
    onFiltersChange({
      ...filters,
      price: DEFAULT_FILTERS.price,
      dietary: DEFAULT_FILTERS.dietary,
      rating: DEFAULT_FILTERS.rating,
      sortBy: DEFAULT_FILTERS.sortBy,
    });
  };

  const activeFiltersCount = countActiveFilters(filters);
  const chipStyle = (active: boolean) => ({
    border: `2px solid ${active ? "var(--red)" : "var(--gray-mid)"}`,
    background: active ? "rgba(217,4,41,0.05)" : "transparent",
    color: active ? "var(--red)" : "var(--black)",
  });

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogPortal>
        <DialogOverlay className="bg-black/50 supports-backdrop-filter:backdrop-blur-none" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed inset-y-0 right-0 z-50 w-full max-w-md h-full bg-white overflow-y-auto outline-none animate-slide-in-right flex flex-col"
          style={{ boxShadow: "-4px 0 20px rgba(0,0,0,0.1)" }}
        >
          {/* Header */}
          <div className="sticky top-0 bg-white z-10 px-6 py-5 border-b" style={{ borderColor: "var(--gray-mid)" }}>
            <div className="flex items-center justify-between mb-4">
              <DialogTitle className="font-black text-2xl leading-normal" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                Filters
              </DialogTitle>
              <DialogClose asChild>
                <button
                  aria-label="Close filters"
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
                >
                  <X className="w-5 h-5" />
                </button>
              </DialogClose>
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

          <div className="p-6 space-y-8 flex-1">
            {/* Sort By */}
            <fieldset>
              <legend className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Sort By</legend>
              <div className="space-y-2">
                {SORT_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => onFiltersChange({ ...filters, sortBy: option.value })}
                    role="radio"
                    aria-checked={filters.sortBy === option.value}
                    className="w-full text-left px-4 py-3 rounded-lg transition-all text-sm font-semibold"
                    style={chipStyle(filters.sortBy === option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </fieldset>

            {/* Price */}
            <fieldset>
              <legend className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Price</legend>
              <div className="grid grid-cols-2 gap-2">
                {PRICE_BANDS.map((band) => (
                  <button
                    key={band.id}
                    onClick={() => onFiltersChange({ ...filters, price: band.id })}
                    role="radio"
                    aria-checked={filters.price === band.id}
                    className="px-3 py-2 rounded-lg text-xs font-semibold transition-all"
                    style={chipStyle(filters.price === band.id)}
                  >
                    {band.label}
                  </button>
                ))}
              </div>
            </fieldset>

            {/* Dietary Preferences */}
            {dietaryTags.some((tag) => !tag.is_allergen) && (
              <fieldset>
                <legend className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Dietary Preferences</legend>
                <div className="grid grid-cols-2 gap-2">
                  {dietaryTags
                    .filter((tag) => !tag.is_allergen)
                    .map((tag) => (
                      <button
                        key={tag.slug}
                        onClick={() => toggleDietary(tag.slug)}
                        role="checkbox"
                        aria-checked={filters.dietary.includes(tag.slug)}
                        className="px-3 py-2 rounded-lg text-xs font-semibold transition-all"
                        style={chipStyle(filters.dietary.includes(tag.slug))}
                      >
                        {tag.icon && <span className="mr-1" aria-hidden="true">{tag.icon}</span>}
                        {tag.name}
                      </button>
                    ))}
                </div>
              </fieldset>
            )}

            {/* Minimum Rating */}
            <fieldset>
              <legend className="font-bold text-sm mb-3" style={{ color: "var(--black)" }}>Minimum Rating</legend>
              <div className="flex gap-2">
                {[0, 3, 4, 5].map((rating) => (
                  <button
                    key={rating}
                    onClick={() => onFiltersChange({ ...filters, rating })}
                    role="radio"
                    aria-checked={filters.rating === rating}
                    aria-label={rating === 0 ? "Any rating" : `${rating} stars and up`}
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
                      <div className="flex gap-0.5" aria-hidden="true">
                        {[...Array(rating)].map((_, i) => (
                          <svg key={i} className="w-3 h-3" viewBox="0 0 20 20" fill="var(--red)">
                            <path d={STAR_PATH} />
                          </svg>
                        ))}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </fieldset>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-white border-t p-6" style={{ borderColor: "var(--gray-mid)" }}>
            <button
              onClick={onClose}
              className="w-full py-4 rounded-full font-bold text-white transition-all hover:opacity-90"
              style={{ background: "var(--red)" }}
            >
              Show {resultsCount} {resultsCount === 1 ? "Dish" : "Dishes"}
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  );
}
