import type { MenuQuery, MenuSort } from "@/lib/api/catalog";

export type ViewMode = "grid" | "list" | "compact";
export type SortOption = MenuSort;

/**
 * Price bands, as fixed kobo bounds. The previous slider ran 0–100 "naira" and
 * filtered by parsing the displayed price string back into a number.
 */
export const PRICE_BANDS = [
  { id: "any", label: "Any price" },
  { id: "under-5000", label: "Under ₦5,000", max: 500_000 },
  { id: "5000-10000", label: "₦5,000 – ₦10,000", min: 500_000, max: 1_000_000 },
  { id: "10000-20000", label: "₦10,000 – ₦20,000", min: 1_000_000, max: 2_000_000 },
  { id: "over-20000", label: "Over ₦20,000", min: 2_000_000 },
] as const;

export type PriceBand = (typeof PRICE_BANDS)[number]["id"];

export const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "popular", label: "Most Popular" },
  { value: "price_asc", label: "Price: Low to High" },
  { value: "price_desc", label: "Price: High to Low" },
  { value: "rating", label: "Highest Rated" },
  { value: "newest", label: "Newest First" },
];

export interface MenuFilters {
  search: string;
  category: string;
  price: PriceBand;
  dietary: string[];
  rating: number;
  sortBy: SortOption;
}

export const DEFAULT_FILTERS: MenuFilters = {
  search: "",
  category: "all",
  price: "any",
  dietary: [],
  rating: 0,
  sortBy: "popular",
};

export const PAGE_SIZE = 24;

export function toMenuQuery(filters: MenuFilters, page = 1): MenuQuery {
  const band = PRICE_BANDS.find((b) => b.id === filters.price);
  return {
    category: filters.category,
    search: filters.search,
    dietary: filters.dietary,
    minPrice: band && "min" in band ? band.min : undefined,
    maxPrice: band && "max" in band ? band.max : undefined,
    minRating: filters.rating || undefined,
    sort: filters.sortBy,
    page,
    limit: PAGE_SIZE,
  };
}

export function countActiveFilters(filters: MenuFilters): number {
  return filters.dietary.length + (filters.price !== "any" ? 1 : 0) + (filters.rating > 0 ? 1 : 0);
}
