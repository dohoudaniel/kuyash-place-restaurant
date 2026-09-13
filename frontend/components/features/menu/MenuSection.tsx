"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchCategories, fetchMenuItems } from "@/lib/api/catalog";
import type { Category, MenuItemSummary } from "@/lib/api/types";
import MenuCategories from "./MenuCategories";
import MenuGrid from "./MenuGrid";

type LoadState = "loading" | "ready" | "error";

const PREFERRED_CATEGORY = "burgers";

function CardSkeleton() {
  return (
    <div className="bg-white rounded-2xl overflow-hidden flex flex-col animate-pulse" style={{ border: "1px solid var(--cream-dark)" }}>
      <div style={{ height: "160px", background: "var(--cream)" }} />
      <div className="p-5 space-y-3">
        <div className="h-4 w-2/3 rounded" style={{ background: "var(--gray-mid)" }} />
        <div className="h-3 w-full rounded" style={{ background: "var(--gray-mid)" }} />
        <div className="h-3 w-1/2 rounded" style={{ background: "var(--gray-mid)" }} />
      </div>
    </div>
  );
}

export default function MenuSection() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [activeSlug, setActiveSlug] = useState("");
  const [items, setItems] = useState<MenuItemSummary[]>([]);
  const [categoriesState, setCategoriesState] = useState<LoadState>("loading");
  const [itemsState, setItemsState] = useState<LoadState>("loading");

  useEffect(() => {
    let cancelled = false;
    fetchCategories()
      .then((all) => {
        if (cancelled) return;
        // Categories with nothing orderable in them are hidden, not shown empty.
        const stocked = all.filter((category) => category.item_count > 0);
        setCategories(stocked);
        setActiveSlug(stocked.find((c) => c.slug === PREFERRED_CATEGORY)?.slug ?? stocked[0]?.slug ?? "");
        setCategoriesState("ready");
        if (stocked.length === 0) setItemsState("ready");
      })
      .catch(() => {
        if (!cancelled) setCategoriesState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!activeSlug) return;
    const controller = new AbortController();
    fetchMenuItems({ category: activeSlug, sort: "popular", limit: 12 }, { signal: controller.signal })
      .then((page) => {
        setItems(page.results);
        setItemsState("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setItemsState("error");
      });
    return () => controller.abort();
  }, [activeSlug]);

  const changeCategory = (slug: string) => {
    if (slug === activeSlug) return;
    setItemsState("loading");
    setActiveSlug(slug);
  };

  const activeCategory = categories.find((c) => c.slug === activeSlug);
  const failed = categoriesState === "error" || itemsState === "error";

  return (
    <section id="menu" className="py-16 md:py-24 px-6 md:px-14" style={{ background: "var(--cream)" }}>
      {/* Heading */}
      <div className="text-center mb-10">
        <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "var(--orange)" }}>
          Our Menu
        </p>
        <h2
          className="font-black text-4xl md:text-5xl"
          style={{ fontFamily: "var(--font-playfair)", color: "var(--brown-dark)" }}
        >
          Explore Our Dishes
        </h2>
        <div className="mt-3 w-12 h-1 rounded-full mx-auto" style={{ background: "var(--orange)" }} />
      </div>

      {/* Category tabs */}
      {categories.length > 0 && (
        <MenuCategories categories={categories} activeSlug={activeSlug} onCategoryChange={changeCategory} />
      )}

      {/* Menu item cards */}
      {failed ? (
        <p role="alert" className="text-center text-sm" style={{ color: "var(--text-muted)" }}>
          We couldn&apos;t load the menu just now. Please refresh to try again.
        </p>
      ) : categoriesState === "loading" || itemsState === "loading" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto" role="status" aria-label="Loading dishes">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : items.length === 0 ? (
        <p className="text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Our menu is being updated. Please check back soon.
        </p>
      ) : (
        <MenuGrid items={items} activeCategory={activeCategory} />
      )}

      {items.length > 0 && (
        <div className="text-center mt-10">
          <Link
            href={activeSlug ? `/menu?category=${encodeURIComponent(activeSlug)}` : "/menu"}
            className="inline-flex px-6 py-3 rounded-full text-sm font-bold transition-all hover:opacity-90"
            style={{ border: "2px solid var(--orange)", color: "var(--orange)" }}
          >
            View Full Menu
          </Link>
        </div>
      )}
    </section>
  );
}
