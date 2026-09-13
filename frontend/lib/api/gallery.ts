/** Gallery photos, uploaded by staff in the Django admin. */
import { api } from "./client";
import type { GalleryCategory, GalleryImage, GalleryImageDetail } from "./types";

export const fetchGallery = (filters: { category?: GalleryCategory; tag?: string } = {}) => {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.tag) params.set("tag", filters.tag);
  const query = params.toString();
  return api<GalleryImage[]>(`/gallery/${query ? `?${query}` : ""}`);
};

export const fetchGalleryImage = (id: string) => api<GalleryImageDetail>(`/gallery/${encodeURIComponent(id)}/`);
