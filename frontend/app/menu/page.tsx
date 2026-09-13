"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import {
  MenuHero,
  MenuFiltersBar,
  MenuCategoriesScroll,
  MenuGrid,
  QuickAddBar,
} from "@/components/features/menu/advanced";
import MenuFiltersPanel from "@/components/features/menu/MenuFilters";
import MenuItemDetailModal from "@/components/features/menu/MenuItemDetailModal";
import {
  DEFAULT_FILTERS,
  toMenuQuery,
  type MenuFilters,
  type ViewMode,
} from "@/components/features/menu/advanced/filters";
import { fetchCategories, fetchDietaryTags, fetchMenuItems } from "@/lib/api/catalog";
import type { Category, DietaryTag, MenuItemSummary } from "@/lib/api/types";

type LoadState = "loading" | "ready" | "error";

function MenuPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [filters, setFilters] = useState<MenuFilters>(() => ({
    ...DEFAULT_FILTERS,
    category: searchParams.get("category") ?? "all",
  }));
  const [categories, setCategories] = useState<Category[]>([]);
  const [dietaryTags, setDietaryTags] = useState<DietaryTag[]>([]);
  const [items, setItems] = useState<MenuItemSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [state, setState] = useState<LoadState>("loading");
  const [loadingMore, setLoadingMore] = useState(false);
  const [menuSize, setMenuSize] = useState<number | null>(null);
  const [topRated, setTopRated] = useState<number | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showFiltersModal, setShowFiltersModal] = useState(false);
  const detailSlug = searchParams.get("item");

  // The vocabulary: categories, dietary tags, and two real counts for the hero.
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchCategories(),
      fetchDietaryTags(),
      fetchMenuItems({ limit: 1 }),
      fetchMenuItems({ minRating: 4, limit: 1 }),
    ])
      .then(([allCategories, tags, everything, rated]) => {
        if (cancelled) return;
        setCategories(allCategories.filter((category) => category.item_count > 0));
        setDietaryTags(tags);
        setMenuSize(everything.count);
        setTopRated(rated.count);
      })
      .catch(() => {
        /* the grid reports its own failure; the hero simply shows no counts */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Search, filter and sort on the server. Typing is debounced; other changes are immediate.
  const queryKey = JSON.stringify(toMenuQuery(filters));
  useEffect(() => {
    const controller = new AbortController();
    const query = JSON.parse(queryKey);
    const timer = window.setTimeout(
      () => {
        setState("loading");
        fetchMenuItems(query, { signal: controller.signal })
          .then((result) => {
            setItems(result.results);
            setTotal(result.count);
            setHasMore(Boolean(result.next));
            setPage(1);
            setState("ready");
          })
          .catch(() => {
            if (!controller.signal.aborted) setState("error");
          });
      },
      query.search ? 300 : 0
    );
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [queryKey]);

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const next = await fetchMenuItems(toMenuQuery(filters, page + 1));
      setItems((current) => [...current, ...next.results]);
      setHasMore(Boolean(next.next));
      setPage(page + 1);
    } catch {
      setState("error");
    } finally {
      setLoadingMore(false);
    }
  };

  const setUrlParam = (name: string, value: string | null) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(name, value);
    else params.delete(name);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  const changeFilters = (next: MenuFilters) => {
    if (next.category !== filters.category) setUrlParam("category", next.category === "all" ? null : next.category);
    setFilters(next);
  };

  const handleSelectItem = (slug: string) => {
    const next = new Set(selectedItems);
    if (next.has(slug)) next.delete(slug);
    else next.add(slug);
    setSelectedItems(next);
  };

  const selectedSummaries = useMemo(
    () => items.filter((item) => selectedItems.has(item.slug)),
    [items, selectedItems]
  );

  return (
    <div className="min-h-screen flex flex-col pt-20 sm:pt-24" style={{ background: "var(--off-white)" }}>
      <main className="flex-1 pb-12">
        {/* Hero Section */}
        <MenuHero
          totalItems={menuSize}
          categoryCount={categories.length}
          dietaryCount={dietaryTags.filter((tag) => !tag.is_allergen).length}
          topRatedCount={topRated}
        />

        <div className="container-custom">
          {/* Categories Horizontal Scroll */}
          <MenuCategoriesScroll
            categories={categories}
            activeCategory={filters.category}
            onCategoryChange={(category) => changeFilters({ ...filters, category })}
          />

          {/* Filters Bar */}
          <MenuFiltersBar
            filters={filters}
            onFiltersChange={changeFilters}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            onShowFilters={() => setShowFiltersModal(true)}
            resultsCount={total}
            isLoading={state === "loading"}
          />

          {/* Menu Grid */}
          {state === "error" && items.length === 0 ? (
            <p role="alert" className="text-center py-16 text-sm" style={{ color: "var(--text-muted)" }}>
              We couldn&apos;t load the menu just now. Please refresh to try again.
            </p>
          ) : state === "loading" && items.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-16" role="status">
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading the menu…</span>
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-16">
              <p className="font-bold" style={{ color: "var(--black)" }}>No dishes match those filters.</p>
              <button
                onClick={() => changeFilters({ ...DEFAULT_FILTERS })}
                className="mt-3 text-sm font-bold transition-all hover:opacity-80"
                style={{ color: "var(--red)" }}
              >
                Clear filters
              </button>
            </div>
          ) : (
            <div style={{ opacity: state === "loading" ? 0.6 : 1 }} className="transition-opacity">
              <MenuGrid
                items={items}
                viewMode={viewMode}
                selectedItems={selectedItems}
                onSelectItem={handleSelectItem}
                onOpenItem={(slug) => setUrlParam("item", slug)}
              />
            </div>
          )}

          {hasMore && items.length > 0 && (
            <div className="text-center mt-8">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="px-8 py-3 rounded-full text-sm font-bold transition-all hover:opacity-90 disabled:opacity-50"
                style={{ border: "2px solid var(--red)", color: "var(--red)", background: "white" }}
              >
                {loadingMore ? "Loading..." : `Load More (${total - items.length} more)`}
              </button>
            </div>
          )}

          {/* Quick Add Bar (when items selected) */}
          {selectedItems.size > 0 && (
            <QuickAddBar
              selectedItems={selectedSummaries}
              onClear={() => setSelectedItems(new Set())}
              onKeepSelected={(slugs) => setSelectedItems(new Set(slugs))}
            />
          )}

          {/* Advanced Filters */}
          <MenuFiltersPanel
            isOpen={showFiltersModal}
            onClose={() => setShowFiltersModal(false)}
            filters={filters}
            onFiltersChange={changeFilters}
            dietaryTags={dietaryTags}
            resultsCount={total}
          />
        </div>
      </main>

      {/* A shared link to one dish: /menu?item=classic-smash-burger */}
      {detailSlug && (
        <MenuItemDetailModal
          slug={detailSlug}
          summary={items.find((item) => item.slug === detailSlug)}
          isOpen
          onClose={() => setUrlParam("item", null)}
        />
      )}
    </div>
  );
}

export default function MenuPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center pt-20" style={{ background: "var(--off-white)" }}>
          <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
        </div>
      }
    >
      <MenuPageContent />
    </Suspense>
  );
}
