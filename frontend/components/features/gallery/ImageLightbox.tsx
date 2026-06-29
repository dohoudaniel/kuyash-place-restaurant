"use client";

import { X, ChevronLeft, ChevronRight, Heart, Share2, Download, ZoomIn, ZoomOut } from "lucide-react";
import type { GalleryImage } from "@/app/gallery/page";
import { useEffect, useState } from "react";

interface ImageLightboxProps {
  image: GalleryImage;
  allImages: GalleryImage[];
  onClose: () => void;
  onNavigate: (image: GalleryImage) => void;
}

export default function ImageLightbox({ image, allImages, onClose, onNavigate }: ImageLightboxProps) {
  const [isFavorite, setIsFavorite] = useState(false);
  const [zoom, setZoom] = useState(1);

  const currentIndex = allImages.findIndex((img) => img.id === image.id);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < allImages.length - 1;

  const handlePrev = () => {
    if (hasPrev) onNavigate(allImages[currentIndex - 1]);
  };

  const handleNext = () => {
    if (hasNext) onNavigate(allImages[currentIndex + 1]);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && hasPrev) handlePrev();
      if (e.key === "ArrowRight" && hasNext) handleNext();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.95)" }}
      onClick={onClose}
    >
      {/* Close Button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110 z-50"
        style={{ background: "rgba(255,255,255,0.1)", color: "white" }}
      >
        <X className="w-6 h-6" />
      </button>

      {/* Navigation Buttons */}
      {hasPrev && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handlePrev();
          }}
          className="absolute left-4 w-12 h-12 rounded-full flex items-center justify-center transition-all hover:scale-110 z-50"
          style={{ background: "rgba(255,255,255,0.1)", color: "white" }}
        >
          <ChevronLeft className="w-8 h-8" />
        </button>
      )}

      {hasNext && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleNext();
          }}
          className="absolute right-4 w-12 h-12 rounded-full flex items-center justify-center transition-all hover:scale-110 z-50"
          style={{ background: "rgba(255,255,255,0.1)", color: "white" }}
        >
          <ChevronRight className="w-8 h-8" />
        </button>
      )}

      {/* Image Container */}
      <div
        className="relative max-w-6xl w-full"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Image */}
        <div className="relative aspect-video rounded-xl overflow-hidden mb-4" style={{ background: "var(--gray-mid)" }}>
          <div
            className="w-full h-full flex items-center justify-center transition-transform"
            style={{ transform: `scale(${zoom})`, background: "var(--gray-light)" }}
          >
            <Eye className="w-24 h-24" style={{ color: "var(--text-muted)" }} />
          </div>

          {/* Zoom Controls */}
          <div className="absolute top-4 left-4 flex gap-2">
            <button
              onClick={() => setZoom((prev) => Math.max(0.5, prev - 0.25))}
              className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
              style={{ background: "rgba(0,0,0,0.5)", color: "white" }}
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((prev) => Math.min(3, prev + 0.25))}
              className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
              style={{ background: "rgba(0,0,0,0.5)", color: "white" }}
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="px-3 h-8 rounded-full text-xs font-bold transition-all hover:scale-110"
              style={{ background: "rgba(0,0,0,0.5)", color: "white" }}
            >
              {Math.round(zoom * 100)}%
            </button>
          </div>
        </div>

        {/* Info Section */}
        <div className="bg-white rounded-xl p-4 sm:p-6">
          <div className="flex items-start justify-between gap-4 mb-3">
            <div className="flex-1">
              <h2 className="font-black text-xl sm:text-2xl mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {image.title}
              </h2>
              <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
                {image.description}
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => setIsFavorite(!isFavorite)}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{ background: isFavorite ? "var(--red)" : "var(--gray-light)", color: isFavorite ? "white" : "var(--black)" }}
              >
                <Heart className={`w-5 h-5 ${isFavorite ? "fill-white" : ""}`} />
              </button>
              <button
                onClick={() => alert("Share functionality")}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{ background: "var(--gray-light)", color: "var(--black)" }}
              >
                <Share2 className="w-5 h-5" />
              </button>
              <button
                onClick={() => alert("Download functionality")}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{ background: "var(--gray-light)", color: "var(--black)" }}
              >
                <Download className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Tags */}
          <div className="flex flex-wrap gap-2 mb-4">
            {image.tags.map((tag) => (
              <span
                key={tag}
                className="px-3 py-1 rounded-full text-xs font-bold"
                style={{ background: "var(--gray-light)", color: "var(--black)" }}
              >
                #{tag}
              </span>
            ))}
          </div>

          {/* Counter */}
          <div className="flex items-center justify-between pt-3" style={{ borderTop: "1px solid var(--gray-mid)" }}>
            <p className="text-sm font-bold" style={{ color: "var(--text-muted)" }}>
              {currentIndex + 1} of {allImages.length}
            </p>
            <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
              Use arrow keys to navigate
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Eye({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  );
}
