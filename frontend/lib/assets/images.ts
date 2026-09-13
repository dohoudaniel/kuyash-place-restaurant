/**
 * Central image registry.
 *
 * HOW TO ADD AN IMAGE
 * -------------------
 * 1. Drop your file into /public/images/<section>/
 * 2. Add a key below pointing to that path (or a remote URL).
 * 3. Reference it anywhere via IMAGES.<key>
 *
 * Sections
 *   hero      – hero section backgrounds / feature shots
 *   (menu photos come from the API — see lib/api/media.ts)
 *   brand     – logos, icons, og-images
 */

export const IMAGES = {
  // ── Hero ────────────────────────────────────────────────────────────────────
  hero: {
    /** Main food plate shown in the right panel */
    mainPlate: "/images/hero/main-plate.jpg",
    /** Floating tomato ingredient */
    tomato: "/images/hero/tomato.png",
    /** Floating garlic ingredient */
    garlic: "/images/hero/garlic.png",
  },

  // ── Academy ─────────────────────────────────────────────────────────────────
  academy: {
    chef: "/images/chef.png",
  },

  // ── Brand ───────────────────────────────────────────────────────────────────
  brand: {
    logo:   "/images/brand/kuyash.png",
    ogImage: "/images/brand/og-image.jpg",
  },
} as const;

