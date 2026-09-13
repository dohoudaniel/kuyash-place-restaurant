"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import GalleryHero from "@/components/features/gallery/GalleryHero";
import GalleryFilters, { type GalleryFilter } from "@/components/features/gallery/GalleryFilters";
import GalleryGrid from "@/components/features/gallery/GalleryGrid";
import ImageLightbox from "@/components/features/gallery/ImageLightbox";
import { fetchGallery } from "@/lib/api/gallery";
import type { GalleryImage } from "@/lib/api/types";

const FILTERS: GalleryFilter[] = ["all", "food", "interior", "events", "team", "ambiance"];

function Gallery() {
  const searchParams = useSearchParams();
  const [images, setImages] = useState<GalleryImage[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<GalleryFilter>("all");
  // A shared link (`/gallery?image=…`) opens straight into the lightbox.
  const [lightboxId, setLightboxId] = useState<string | null>(searchParams.get("image"));

  useEffect(() => {
    let cancelled = false;
    fetchGallery()
      .then((data) => !cancelled && setImages(data))
      .catch(() => !cancelled && setLoadError(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const all = images ?? [];
  const filteredImages = selectedCategory === "all" ? all : all.filter((img) => img.category === selectedCategory);
  const lightboxImage = all.find((img) => img.id === lightboxId) ?? null;
  // Browse neighbours within the current filter, unless a shared link points outside it.
  const lightboxSet = lightboxImage && filteredImages.includes(lightboxImage) ? filteredImages : all;

  const counts = Object.fromEntries(
    FILTERS.map((filter) => [filter, filter === "all" ? all.length : all.filter((img) => img.category === filter).length])
  ) as Record<GalleryFilter, number>;

  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <GalleryHero totalImages={all.length} />
      <div className="container-custom py-6 sm:py-8">
        <GalleryFilters selectedCategory={selectedCategory} onSelectCategory={setSelectedCategory} counts={counts} />

        {loadError ? (
          <p role="alert" className="text-center py-12 text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
            We couldn&apos;t load the gallery. Please check your connection and try again.
          </p>
        ) : images === null ? (
          <div className="flex justify-center py-12" role="status" aria-label="Loading photos">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
          </div>
        ) : (
          <GalleryGrid images={filteredImages} onImageClick={(image) => setLightboxId(image.id)} />
        )}
      </div>

      {lightboxImage && (
        <ImageLightbox
          image={lightboxImage}
          allImages={lightboxSet}
          onClose={() => setLightboxId(null)}
          onNavigate={(image) => setLightboxId(image.id)}
        />
      )}
    </div>
  );
}

export default function GalleryPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
        </div>
      }
    >
      <Gallery />
    </Suspense>
  );
}
