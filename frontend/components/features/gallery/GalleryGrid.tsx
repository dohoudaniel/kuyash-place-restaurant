"use client";

import { useState } from "react";
import Image from "next/image";
import { Check, Eye, Share2 } from "lucide-react";
import { mediaUrl } from "@/lib/api/media";
import type { GalleryImage } from "@/lib/api/types";
import { shareLink } from "@/lib/share";

interface GalleryGridProps {
  images: GalleryImage[];
  onImageClick: (image: GalleryImage) => void;
}

/**
 * Photos uploaded by the team. The previous grid showed a placeholder icon for
 * every tile — its image keys had no files — and its Save and Share buttons
 * were local state and `alert()`.
 */
export default function GalleryGrid({ images, onImageClick }: GalleryGridProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const share = async (image: GalleryImage, e: React.MouseEvent) => {
    e.stopPropagation();
    if ((await shareLink(image.title, `/gallery?image=${image.id}`)) === "copied") {
      setCopiedId(image.id);
      window.setTimeout(() => setCopiedId((current) => (current === image.id ? null : current)), 2000);
    }
  };

  if (images.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-bold" style={{ color: "var(--text-muted)" }}>
          No photos here yet
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
      {images.map((image) => {
        const src = mediaUrl(image.image_url);
        return (
          <div
            key={image.id}
            role="button"
            tabIndex={0}
            aria-label={`View ${image.title}`}
            onClick={() => onImageClick(image)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onImageClick(image);
              }
            }}
            className="group relative aspect-square rounded-xl overflow-hidden cursor-pointer transition-all hover:shadow-2xl hover:-translate-y-1"
            style={{ background: "var(--gray-mid)" }}
          >
            {src ? (
              <Image
                src={src}
                alt={image.alt_text}
                fill
                sizes="(max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                className="object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center" style={{ background: "var(--gray-light)" }}>
                <Eye className="w-12 h-12" style={{ color: "var(--text-muted)" }} />
              </div>
            )}

            {/* Overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition-opacity">
              <div className="absolute bottom-0 left-0 right-0 p-3 sm:p-4">
                <h3 className="font-black text-sm sm:text-base text-white mb-1">{image.title}</h3>
                {image.description && <p className="text-xs text-white/80 mb-2 line-clamp-1">{image.description}</p>}

                {/* Tags */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {image.tags.slice(0, 2).map((tag) => (
                    <span
                      key={tag.slug}
                      className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
                      style={{ background: "rgba(255,255,255,0.2)" }}
                    >
                      {tag.name}
                    </span>
                  ))}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={(e) => share(image, e)}
                    aria-label={`Share ${image.title}`}
                    className="px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1 transition-all"
                    style={{ background: "rgba(255,255,255,0.2)", color: "white" }}
                  >
                    {copiedId === image.id ? <Check className="w-3 h-3" /> : <Share2 className="w-3 h-3" />}
                    {copiedId === image.id && "Link copied"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
