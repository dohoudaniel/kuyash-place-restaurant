"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { X, ChevronLeft, ChevronRight, Share2, Download, ZoomIn, ZoomOut, Check, Eye } from "lucide-react";
import { mediaUrl } from "@/lib/api/media";
import type { GalleryImage } from "@/lib/api/types";
import { shareLink } from "@/lib/share";

interface ImageLightboxProps {
  image: GalleryImage;
  allImages: GalleryImage[];
  onClose: () => void;
  onNavigate: (image: GalleryImage) => void;
}

export default function ImageLightbox({ image, allImages, onClose, onNavigate }: ImageLightboxProps) {
  const [zoom, setZoom] = useState(1);
  const [copied, setCopied] = useState(false);

  const currentIndex = allImages.findIndex((img) => img.id === image.id);
  const previous = currentIndex > 0 ? allImages[currentIndex - 1] : null;
  const next = currentIndex >= 0 && currentIndex < allImages.length - 1 ? allImages[currentIndex + 1] : null;
  const src = mediaUrl(image.image_url);

  const go = (target: GalleryImage | null) => {
    if (!target) return;
    setZoom(1);
    onNavigate(target);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && previous) {
        setZoom(1);
        onNavigate(previous);
      }
      if (e.key === "ArrowRight" && next) {
        setZoom(1);
        onNavigate(next);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [previous, next, onClose, onNavigate]);

  const handleShare = async () => {
    if ((await shareLink(image.title, `/gallery?image=${image.id}`)) === "copied") {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={image.title}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.95)" }}
      onClick={onClose}
    >
      {/* Close Button */}
      <button
        onClick={onClose}
        aria-label="Close"
        className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110 z-50"
        style={{ background: "rgba(255,255,255,0.1)", color: "white" }}
      >
        <X className="w-6 h-6" />
      </button>

      {/* Navigation Buttons */}
      {previous && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            go(previous);
          }}
          aria-label="Previous photo"
          className="absolute left-4 w-12 h-12 rounded-full flex items-center justify-center transition-all hover:scale-110 z-50"
          style={{ background: "rgba(255,255,255,0.1)", color: "white" }}
        >
          <ChevronLeft className="w-8 h-8" />
        </button>
      )}

      {next && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            go(next);
          }}
          aria-label="Next photo"
          className="absolute right-4 w-12 h-12 rounded-full flex items-center justify-center transition-all hover:scale-110 z-50"
          style={{ background: "rgba(255,255,255,0.1)", color: "white" }}
        >
          <ChevronRight className="w-8 h-8" />
        </button>
      )}

      <div
        className="w-full max-w-5xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Image */}
        <div className="relative aspect-video rounded-xl overflow-hidden mb-4" style={{ background: "var(--gray-mid)" }}>
          <div
            className="relative w-full h-full flex items-center justify-center transition-transform"
            style={{ transform: `scale(${zoom})`, background: "var(--gray-light)" }}
          >
            {src ? (
              <Image src={src} alt={image.alt_text} fill sizes="(max-width: 1024px) 100vw, 1024px" className="object-contain" priority />
            ) : (
              <Eye className="w-24 h-24" style={{ color: "var(--text-muted)" }} />
            )}
          </div>

          {/* Zoom Controls */}
          <div className="absolute top-4 left-4 flex gap-2">
            <button
              onClick={() => setZoom((prev) => Math.max(0.5, prev - 0.25))}
              aria-label="Zoom out"
              className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
              style={{ background: "rgba(0,0,0,0.5)", color: "white" }}
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((prev) => Math.min(3, prev + 0.25))}
              aria-label="Zoom in"
              className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110"
              style={{ background: "rgba(0,0,0,0.5)", color: "white" }}
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(1)}
              aria-label="Reset zoom"
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
              {image.description && (
                <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
                  {image.description}
                </p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 items-center">
              {copied && (
                <span className="text-xs font-bold" style={{ color: "var(--text-muted)" }}>Link copied</span>
              )}
              <button
                onClick={handleShare}
                aria-label="Share this photo"
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{ background: "var(--gray-light)", color: "var(--black)" }}
              >
                {copied ? <Check className="w-5 h-5" /> : <Share2 className="w-5 h-5" />}
              </button>
              {src && (
                <a
                  href={src}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Download this photo"
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                  style={{ background: "var(--gray-light)", color: "var(--black)" }}
                >
                  <Download className="w-5 h-5" />
                </a>
              )}
            </div>
          </div>

          {/* Tags */}
          {image.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {image.tags.map((tag) => (
                <span
                  key={tag.slug}
                  className="px-3 py-1 rounded-full text-xs font-bold"
                  style={{ background: "var(--gray-light)", color: "var(--black)" }}
                >
                  #{tag.name}
                </span>
              ))}
            </div>
          )}

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
