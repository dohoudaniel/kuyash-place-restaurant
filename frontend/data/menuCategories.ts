export interface MenuCategory {
  label: string;
  slug: string;
  emoji: string;
}

export const MENU_CATEGORIES: MenuCategory[] = [
  { label: "What's Hot", slug: "whats-hot", emoji: "🔥" },
  { label: "Burgers", slug: "burgers", emoji: "🍔" },
  { label: "Chickens and Salads", slug: "chicken-salad", emoji: "🍗" },
  { label: "Tacos, Fries and Sides", slug: "tacos", emoji: "🌮" },
  { label: "Breakfast", slug: "breakfast", emoji: "🥞" },
  { label: "Desserts and Drinks", slug: "desserts", emoji: "🍰" },
];
