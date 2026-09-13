import { API_ORIGIN } from "./client";

/**
 * Resolve an image URL from the API.
 *
 * In production images are absolute Supabase Storage URLs and pass through
 * untouched. In local development Django serves them from `/media/…` on its own
 * origin, which the browser would otherwise resolve against the Next.js origin.
 */
export function mediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  return `${API_ORIGIN}${url.startsWith("/") ? "" : "/"}${url}`;
}
