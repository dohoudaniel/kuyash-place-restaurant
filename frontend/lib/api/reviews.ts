/**
 * Dish reviews.
 *
 * Reviews are tied to a delivered order line on the server, so there is no
 * name or email to collect: the author is the signed-in customer.
 */
import { api } from "./client";
import type { OwnReview, PaginatedReviews, ReviewHelpful } from "./types";

export type ReviewSort = "newest" | "helpful" | "highest" | "lowest";

export interface ReviewInput {
  rating: number;
  title: string;
  comment: string;
  recommends: boolean;
}

export const fetchReviews = (slug: string, { sort = "newest", page = 1, limit = 5 }: { sort?: ReviewSort; page?: number; limit?: number } = {}) =>
  api<PaginatedReviews>(`/reviews/?${new URLSearchParams({ item: slug, sort, page: String(page), limit: String(limit) })}`);

export const createReview = (orderLine: string, input: ReviewInput) =>
  api<OwnReview>("/reviews/", { method: "POST", body: { order_line: orderLine, ...input } });

export const fetchOwnReview = (id: string) => api<OwnReview>(`/reviews/${id}/`);

export const updateReview = (id: string, input: Partial<ReviewInput>) =>
  api<OwnReview>(`/reviews/${id}/`, { method: "PATCH", body: input });

export const deleteReview = (id: string) => api<void>(`/reviews/${id}/`, { method: "DELETE" });

export const markHelpful = (id: string) => api<ReviewHelpful>(`/reviews/${id}/helpful/`, { method: "POST" });
