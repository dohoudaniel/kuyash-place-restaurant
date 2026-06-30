"use client";

import { useState, useMemo } from "react";
import {
  MenuHero,
  MenuFiltersBar,
  MenuCategoriesScroll,
  MenuGrid,
  MenuViewToggle,
  QuickAddBar,
} from "@/components/features/menu/advanced";
import { MENU_CATEGORIES, MENU_ITEMS } from "@/lib/data/menu";
import type { MenuItem } from "@/lib/types";

export type ViewMode = "grid" | "list" | "compact";
export type SortOption = "popular" | "price-low" | "price-high" | "rating" | "newest";

export interface MenuFilters {
  search: string;
  category: string;
  priceRange: [number, number];
  dietary: string[];
  rating: number;
  sortBy: SortOption;
}

export default function MenuPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [filters, setFilters] = useState<MenuFilters>({
    search: "",
    category: "all",
    priceRange: [0, 100],
    dietary: [],
    rating: 0,
    sortBy: "popular",
  });
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showFiltersModal, setShowFiltersModal] = useState(false);

  // Get all menu items
  const allItems = useMemo(() => {
    const items: (MenuItem & { category: string })[] = [];
    Object.entries(MENU_ITEMS).forEach(([category, categoryItems]) => {
      categoryItems.forEach(item => {
        items.push({
          ...item,
          category,
        });
      });
    });
    return items;
  }, []);

  // Filter and sort items
  const filteredItems = useMemo(() => {
    let items = allItems;

    // Search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      items = items.filter(
        item =>
          item.name.toLowerCase().includes(searchLower) ||
          item.description.toLowerCase().includes(searchLower)
      );
    }

    // Category filter
    if (filters.category !== "all") {
      items = items.filter(item => item.category === filters.category);
    }

    // Price filter
    items = items.filter(item => {
      const price = parseFloat(item.price.replace(/[^\d.]/g, ""));
      return price >= filters.priceRange[0] && price <= filters.priceRange[1];
    });

    // Rating filter
    if (filters.rating > 0) {
      // Mock: all items have 5.0 rating for now
      items = items.filter(() => 5.0 >= filters.rating);
    }

    // Dietary filters
    if (filters.dietary.length > 0) {
      // Mock: would filter based on item dietary properties
    }

    // Sort items
    items = [...items].sort((a, b) => {
      switch (filters.sortBy) {
        case "price-low":
          return (
            parseFloat(a.price.replace(/[^\d.]/g, "")) -
            parseFloat(b.price.replace(/[^\d.]/g, ""))
          );
        case "price-high":
          return (
            parseFloat(b.price.replace(/[^\d.]/g, "")) -
            parseFloat(a.price.replace(/[^\d.]/g, ""))
          );
        case "rating":
          return 0; // Mock: all have same rating
        case "newest":
          return 0; // Mock: no date property
        default:
          return 0;
      }
    });

    return items;
  }, [allItems, filters]);

  const handleSelectItem = (itemId: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  const handleClearSelection = () => {
    setSelectedItems(new Set());
  };

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-12">
        {/* Hero Section */}
        <MenuHero totalItems={allItems.length} />

        <div className="container-custom">
          {/* Categories Horizontal Scroll */}
          <MenuCategoriesScroll
            categories={MENU_CATEGORIES}
            activeCategory={filters.category}
            onCategoryChange={(category) => setFilters({ ...filters, category })}
          />

          {/* Filters Bar */}
          <MenuFiltersBar
            filters={filters}
            onFiltersChange={setFilters}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            onShowFilters={() => setShowFiltersModal(true)}
            resultsCount={filteredItems.length}
          />

          {/* Menu Grid */}
          <MenuGrid
            items={filteredItems}
            viewMode={viewMode}
            selectedItems={selectedItems}
            onSelectItem={handleSelectItem}
          />

          {/* Quick Add Bar (when items selected) */}
          {selectedItems.size > 0 && (
            <QuickAddBar
              selectedCount={selectedItems.size}
              selectedItems={Array.from(selectedItems)
                .map(id => filteredItems.find(item =>
                  (item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-")) === id
                ))
                .filter(Boolean) as MenuItem[]}
              onClear={handleClearSelection}
            />
          )}

          {/* Advanced Filters Modal */}
          {showFiltersModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
              {/* Modal content will be in separate component */}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
