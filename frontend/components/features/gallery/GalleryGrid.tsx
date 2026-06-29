"use client";

import { Eye, Heart, Share2 } from "lucide-react";
import type { GalleryImage } from "@/app/gallery/page";
import { useState } from "react";

interface GalleryGridProps {
  images: GalleryImage[];
  onImageClick: (image: GalleryImage) => void;
}

export default function GalleryGrid({ images, onImageClick }: GalleryGridProps) {
  const [favorites, setFavorites] = useState<Set<string>>(new Set());

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setFavorites((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  if (images.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-bold" style={{ color: "var(--text-muted)" }}>
          No images found in this category
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
      {images.map((image) => {
        const isFavorite = favorites.has(image.id);
        return (
          <div
            key={image.id}
            onClick={() => onImageClick(image)}
            className="group relative aspect-square rounded-xl overflow-hidden cursor-pointer transition-all hover:shadow-2xl hover:-translate-y-1"
            style={{ background: "var(--gray-mid)" }}
          >
            {/* Placeholder Image */}
            <div className="w-full h-full flex items-center justify-center" style={{ background: "var(--gray-light)" }}>
              <Eye className="w-12 h-12" style={{ color: "var(--text-muted)" }} />
            </div>

            {/* Overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="absolute bottom-0 left-0 right-0 p-3 sm:p-4">
                <h3 className="font-black text-sm sm:text-base text-white mb-1">{image.title}</h3>
                <p className="text-xs text-white/80 mb-2 line-clamp-1">{image.description}</p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {image.tags.slice(0, 2).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
                      style={{ background: "rgba(255,255,255,0.2)" }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={(e) => toggleFavorite(image.id, e)}
                    className="flex-1 px-3 py-1.5 rounded-lg font-bold text-xs flex items-center justify-center gap-1 transition-all"
                    style={{
                      background: isFavorite ? "var(--red)" : "rgba(255,255,255,0.2)",
                      color: "white",
                    }}
                  >
                    <Heart className={`w-3 h-3 ${isFavorite ? "fill-white" : ""}`} />
                    {isFavorite ? "Saved" : "Save"}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      alert("Share functionality");
                    }}
                    className="px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1 transition-all"
                    style={{ background: "rgba(255,255,255,0.2)", color: "white" }}
                  >
                    <Share2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>

            {/* Favorite Badge */}
            {isFavorite && (
              <div className="absolute top-2 right-2 w-8 h-8 rounded-full flex items-center justify-center" style={{ background: "var(--red)" }}>
                <Heart className="w-4 h-4 text-white fill-white" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
