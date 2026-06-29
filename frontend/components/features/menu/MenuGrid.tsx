"use client";

import type { MenuItem as MenuItemType, MenuCategory } from "@/lib/types";
import MenuItem from "./MenuItem";

interface MenuGridProps {
  items: MenuItemType[];
  activeCategory?: MenuCategory;
}

export default function MenuGrid({ items, activeCategory }: MenuGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
      {items.map((item) => (
        <MenuItem key={item.name} item={item} activeCategory={activeCategory} />
      ))}
    </div>
  );
}
