/**
 * Catalogue reads and item quotes.
 *
 * Filtering, searching and sorting happen on the server. The previous menu page
 * filtered in the browser, parsed prices out of strings, and two of its five
 * sort options were `return 0`.
 */
import { api } from "./client";
import type {
  Category,
  DietaryTag,
  ItemQuote,
  MenuItemDetail,
  MenuItemSummary,
  PaginatedMenuItems,
} from "./types";

export type MenuSort = "popular" | "price_asc" | "price_desc" | "rating" | "newest";

export interface MenuQuery {
  category?: string;
  search?: string;
  dietary?: string[];
  /** Kobo. */
  minPrice?: number;
  /** Kobo. */
  maxPrice?: number;
  minRating?: number;
  sort?: MenuSort;
  page?: number;
  limit?: number;
}

function toQueryString(query: MenuQuery): string {
  const params = new URLSearchParams();
  if (query.category && query.category !== "all") params.set("category", query.category);
  if (query.search?.trim()) params.set("search", query.search.trim());
  if (query.dietary?.length) params.set("dietary", query.dietary.join(","));
  if (query.minPrice !== undefined) params.set("min_price", String(query.minPrice));
  if (query.maxPrice !== undefined) params.set("max_price", String(query.maxPrice));
  if (query.minRating) params.set("min_rating", String(query.minRating));
  if (query.sort) params.set("sort", query.sort);
  if (query.page) params.set("page", String(query.page));
  if (query.limit) params.set("limit", String(query.limit));
  const text = params.toString();
  return text ? `?${text}` : "";
}

export const fetchCategories = () => api<Category[]>("/catalog/categories/");

export const fetchDietaryTags = () => api<DietaryTag[]>("/catalog/dietary-tags/");

export const fetchFeatured = () => api<MenuItemSummary[]>("/catalog/featured/");

export const fetchMenuItems = (query: MenuQuery = {}, init: { signal?: AbortSignal } = {}) =>
  api<PaginatedMenuItems>(`/catalog/items/${toQueryString(query)}`, init);

export const fetchMenuItem = (slug: string) =>
  api<MenuItemDetail>(`/catalog/items/${encodeURIComponent(slug)}/`);

export interface QuoteInput {
  menu_item: string;
  quantity: number;
  variant: string | null;
  modifiers: { modifier: string; quantity?: number }[];
}

/** Price a configuration with the same service the cart charges with. */
export const quoteItem = (input: QuoteInput, init: { signal?: AbortSignal } = {}) =>
  api<ItemQuote>("/cart/quote/", { method: "POST", body: input, signal: init.signal });
