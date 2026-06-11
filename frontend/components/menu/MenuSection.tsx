"use client";

import { useState } from "react";
import Image from "next/image";
import { MENU_CATEGORIES, MENU_ITEMS } from "@/src/lib/data/menu";
import { IMAGES, type ImageKey } from "@/src/lib/assets/images";

export default function MenuSection() {
  const [activeSlug, setActiveSlug] = useState("burgers");

  const items = MENU_ITEMS[activeSlug] ?? [];
  const activeCategory = MENU_CATEGORIES.find((c) => c.slug === activeSlug);

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
      <div className="flex items-center justify-center flex-wrap gap-3 mb-12">
        {MENU_CATEGORIES.map((cat) => {
          const isActive = cat.slug === activeSlug;
          return (
            <button
              key={cat.slug}
              onClick={() => setActiveSlug(cat.slug)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 hover:scale-105 active:scale-95"
              style={{
                background: isActive ? "var(--orange)" : "white",
                color: isActive ? "white" : "var(--brown-mid)",
                border: isActive ? "none" : "1.5px solid var(--cream-dark)",
                boxShadow: isActive ? "0 4px 14px rgba(224,91,43,0.35)" : "none",
              }}
            >
              <span aria-hidden="true">{cat.emoji}</span>
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* Menu item cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {items.map((item) => {
          const imageSrc = item.imageKey
            ? IMAGES.menu[item.imageKey as ImageKey]
            : null;

          return (
            <div
              key={item.name}
              className="bg-white rounded-2xl overflow-hidden flex flex-col transition-all duration-200 hover:shadow-lg hover:-translate-y-1 cursor-pointer"
              style={{ border: "1px solid var(--cream-dark)" }}
            >
              {/* Image area */}
              <div
                className="relative w-full flex items-center justify-center"
                style={{ height: "160px", background: "var(--cream)" }}
              >
                {imageSrc ? (
                  <Image
                    src={imageSrc}
                    alt={item.name}
                    fill
                    className="object-cover"
                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                  />
                ) : (
                  <span className="text-5xl" aria-hidden="true">
                    {activeCategory?.emoji}
                  </span>
                )}
              </div>

              {/* Content */}
              <div className="p-5 flex flex-col gap-3 flex-1">
                <div>
                  <h3 className="font-bold text-base" style={{ color: "var(--brown-dark)" }}>
                    {item.name}
                  </h3>
                  <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    {item.description}
                  </p>
                </div>

                {/* Star rating */}
                <div className="flex items-center gap-1">
                  {[...Array(5)].map((_, i) => (
                    <svg key={i} className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="var(--red)">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                  <span className="text-xs ml-1" style={{ color: "var(--text-muted)" }}>5.0</span>
                </div>

                <div className="flex items-center justify-between mt-auto pt-1">
                  <span className="font-black text-lg" style={{ color: "var(--red)" }}>
                    {item.price}
                  </span>
                  <button
                    className="px-4 py-2 rounded-full text-xs font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95"
                    style={{ background: "var(--red)" }}
                  >
                    Add to cart
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
