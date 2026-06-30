"use client";

import { useState } from "react";
import GalleryHero from "@/components/features/gallery/GalleryHero";
import GalleryFilters from "@/components/features/gallery/GalleryFilters";
import GalleryGrid from "@/components/features/gallery/GalleryGrid";
import ImageLightbox from "@/components/features/gallery/ImageLightbox";

export type GalleryCategory = "all" | "food" | "interior" | "events" | "team" | "ambiance";

export interface GalleryImage {
  id: string;
  category: GalleryCategory;
  title: string;
  description: string;
  imageKey: string;
  tags: string[];
}

const GALLERY_IMAGES: GalleryImage[] = [
  // Food
  { id: "1", category: "food", title: "Signature Jollof Rice", description: "Our award-winning signature dish", imageKey: "jollof", tags: ["main course", "signature"] },
  { id: "2", category: "food", title: "Grilled Suya Platter", description: "Spicy Nigerian street food", imageKey: "suya", tags: ["appetizer", "spicy"] },
  { id: "3", category: "food", title: "Fresh Seafood", description: "Daily catch from local markets", imageKey: "seafood", tags: ["seafood", "fresh"] },
  { id: "4", category: "food", title: "Traditional Pounded Yam", description: "Served with Egusi soup", imageKey: "pounded-yam", tags: ["traditional", "main course"] },
  { id: "5", category: "food", title: "Gourmet Burgers", description: "Handcrafted with premium beef", imageKey: "burger", tags: ["western", "popular"] },
  { id: "6", category: "food", title: "Artisan Desserts", description: "Sweet endings to perfect meals", imageKey: "dessert", tags: ["dessert", "sweet"] },

  // Interior
  { id: "7", category: "interior", title: "Main Dining Hall", description: "Elegant and spacious seating", imageKey: "dining-hall", tags: ["indoor", "elegant"] },
  { id: "8", category: "interior", title: "Private Dining Room", description: "Exclusive space for special occasions", imageKey: "private-room", tags: ["private", "luxury"] },
  { id: "9", category: "interior", title: "Outdoor Patio", description: "Al fresco dining experience", imageKey: "patio", tags: ["outdoor", "garden"] },
  { id: "10", category: "interior", title: "Bar Area", description: "Craft cocktails and premium spirits", imageKey: "bar", tags: ["bar", "drinks"] },

  // Events
  { id: "11", category: "events", title: "Wedding Reception", description: "Celebrating love in style", imageKey: "wedding", tags: ["wedding", "celebration"] },
  { id: "12", category: "events", title: "Corporate Dinner", description: "Professional event hosting", imageKey: "corporate", tags: ["corporate", "business"] },
  { id: "13", category: "events", title: "Birthday Party", description: "Making memories special", imageKey: "birthday", tags: ["birthday", "party"] },
  { id: "14", category: "events", title: "Live Music Night", description: "Entertainment and dining", imageKey: "music", tags: ["music", "entertainment"] },

  // Team
  { id: "15", category: "team", title: "Chef Emmanuel", description: "Head Chef and Culinary Director", imageKey: "chef", tags: ["chef", "team"] },
  { id: "16", category: "team", title: "Kitchen Crew", description: "Our talented culinary team", imageKey: "kitchen-team", tags: ["team", "kitchen"] },
  { id: "17", category: "team", title: "Service Staff", description: "Dedicated to your experience", imageKey: "service", tags: ["team", "service"] },

  // Ambiance
  { id: "18", category: "ambiance", title: "Evening Atmosphere", description: "Romantic candlelit dining", imageKey: "evening", tags: ["romantic", "night"] },
  { id: "19", category: "ambiance", title: "Daytime Vibes", description: "Bright and welcoming", imageKey: "daytime", tags: ["bright", "lunch"] },
  { id: "20", category: "ambiance", title: "Table Setting", description: "Attention to every detail", imageKey: "table", tags: ["details", "elegant"] },
];

export default function GalleryPage() {
  const [selectedCategory, setSelectedCategory] = useState<GalleryCategory>("all");
  const [lightboxImage, setLightboxImage] = useState<GalleryImage | null>(null);

  const filteredImages = selectedCategory === "all"
    ? GALLERY_IMAGES
    : GALLERY_IMAGES.filter(img => img.category === selectedCategory);

  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <GalleryHero totalImages={GALLERY_IMAGES.length} />
      <div className="container-custom py-6 sm:py-8">
        <GalleryFilters
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          counts={{
            all: GALLERY_IMAGES.length,
            food: GALLERY_IMAGES.filter(i => i.category === "food").length,
            interior: GALLERY_IMAGES.filter(i => i.category === "interior").length,
            events: GALLERY_IMAGES.filter(i => i.category === "events").length,
            team: GALLERY_IMAGES.filter(i => i.category === "team").length,
            ambiance: GALLERY_IMAGES.filter(i => i.category === "ambiance").length,
          }}
        />
        <GalleryGrid images={filteredImages} onImageClick={setLightboxImage} />
      </div>

      {lightboxImage && (
        <ImageLightbox
          image={lightboxImage}
          allImages={filteredImages}
          onClose={() => setLightboxImage(null)}
          onNavigate={setLightboxImage}
        />
      )}
    </div>
  );
}
