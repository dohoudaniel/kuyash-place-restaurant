// ─── Navigation ───────────────────────────────────────────────────────────────

export interface NavLink {
  label: string;
  href: string;
}

// ─── Menu ─────────────────────────────────────────────────────────────────────

export interface MenuCategory {
  label: string;
  slug: string;
  emoji: string;
}

export interface MenuItem {
  name: string;
  description: string;
  price: string;
  /** Key into the images registry, e.g. "burgerClassic" */
  imageKey?: string;
}

export type MenuCatalog = Record<string, MenuItem[]>;

// ─── Hero ─────────────────────────────────────────────────────────────────────

export interface HeroStat {
  value: string;
  label: string;
}
