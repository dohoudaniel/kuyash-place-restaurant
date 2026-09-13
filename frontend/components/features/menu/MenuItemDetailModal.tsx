"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { X, Plus, Minus, ShoppingCart, Heart, Share2, AlertCircle, Check, Loader2 } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Dialog, DialogClose, DialogOverlay, DialogPortal, DialogTitle } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api/client";
import { fetchMenuItem, quoteItem } from "@/lib/api/catalog";
import { mediaUrl } from "@/lib/api/media";
import type { ItemQuote, MenuItemDetail, MenuItemSummary, ModifierGroup } from "@/lib/api/types";
import { useCartStore } from "@/lib/store/cartStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";

interface MenuItemDetailModalProps {
  slug: string;
  /** What the card already knows, shown while the full item loads. */
  summary?: Pick<MenuItemSummary, "name" | "description" | "price" | "image_url">;
  fallbackEmoji?: string;
  isOpen: boolean;
  onClose: () => void;
}

const MAX_QUANTITY = 99;

function minimumFor(group: ModifierGroup): number {
  return group.min_select ?? 0;
}

function maximumFor(group: ModifierGroup): number {
  return group.max_select ?? 1;
}

/**
 * A dish's sizes and options, from the dish itself.
 *
 * Replaces one hardcoded `MOCK_CUSTOMIZATIONS` array rendered on every item —
 * pancakes were offered extra cheese — whose selections were then priced by
 * string parsing in the browser. The options here are the dish's own, the rules
 * (required, up to N) are the server's, and the total on the button is a server
 * quote computed by the same code that will charge for it.
 */
export default function MenuItemDetailModal({ slug, summary, fallbackEmoji, isOpen, onClose }: MenuItemDetailModalProps) {
  const addItem = useCartStore((state) => state.addItem);
  const { addItem: addToWishlist, removeItem: removeFromWishlist, isInWishlist } = useWishlistStore();

  const [detail, setDetail] = useState<MenuItemDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [variantId, setVariantId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Record<string, string[]>>({});
  const [quantity, setQuantity] = useState(1);
  const [specialInstructions, setSpecialInstructions] = useState("");
  const [quote, setQuote] = useState<ItemQuote | null>(null);
  const [addState, setAddState] = useState<"idle" | "adding" | "added">("idle");
  const [addError, setAddError] = useState<string | null>(null);
  const [shared, setShared] = useState(false);

  // Load the full item the first time the dialog opens for it.
  useEffect(() => {
    if (!isOpen || detail?.slug === slug) return;
    let cancelled = false;
    fetchMenuItem(slug)
      .then((item) => {
        if (cancelled) return;
        setDetail(item);
        setLoadError(null);
        setVariantId(item.variants.find((variant) => variant.is_default)?.id ?? null);
        setSelected(
          Object.fromEntries(
            item.modifier_groups.map((group) => [
              group.id,
              group.modifiers.filter((m) => m.is_default && m.is_available !== false).map((m) => m.id),
            ])
          )
        );
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof ApiError && err.status === 404 ? "This dish is no longer on the menu." : "We couldn't load this dish. Please try again.");
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, slug, detail?.slug]);

  const groups = detail?.modifier_groups ?? [];
  const missing = groups.filter((group) => (selected[group.id]?.length ?? 0) < minimumFor(group));
  const canConfigure = Boolean(detail) && missing.length === 0;

  // Ask the server what this configuration costs, shortly after it settles.
  useEffect(() => {
    if (!isOpen || !detail || missing.length > 0) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      quoteItem(
        {
          menu_item: detail.slug,
          quantity,
          variant: variantId,
          modifiers: Object.values(selected).flat().map((modifier) => ({ modifier })),
        },
        { signal: controller.signal }
      )
        .then(setQuote)
        .catch(() => {
          /* the button falls back to no total; adding still validates */
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [isOpen, detail, missing.length, quantity, variantId, selected]);

  const handleClose = () => {
    setQuantity(1);
    setSpecialInstructions("");
    setAddState("idle");
    setAddError(null);
    onClose();
  };

  const toggleModifier = (group: ModifierGroup, modifierId: string) => {
    setSelected((previous) => {
      const current = previous[group.id] ?? [];
      const max = maximumFor(group);
      if (max <= 1) {
        const deselect = current.includes(modifierId) && minimumFor(group) === 0;
        return { ...previous, [group.id]: deselect ? [] : [modifierId] };
      }
      if (current.includes(modifierId)) {
        return { ...previous, [group.id]: current.filter((id) => id !== modifierId) };
      }
      if (current.length >= max) return previous;
      return { ...previous, [group.id]: [...current, modifierId] };
    });
  };

  const handleAddToCart = async () => {
    if (!detail || !canConfigure) return;
    setAddState("adding");
    setAddError(null);
    try {
      await addItem({
        menu_item: detail.slug,
        quantity,
        variant: variantId,
        modifiers: Object.values(selected).flat().map((modifier) => ({ modifier })),
        special_instructions: specialInstructions,
      });
      setAddState("added");
      window.setTimeout(handleClose, 900);
    } catch (err) {
      setAddState("idle");
      setAddError(err instanceof ApiError ? err.message : "Couldn't add that. Please try again.");
    }
  };

  const name = detail?.name ?? summary?.name ?? "";
  const description = detail?.description ?? summary?.description ?? "";
  const price = detail?.price ?? summary?.price ?? null;
  const imageSrc = mediaUrl(detail?.image_url ?? summary?.image_url);
  const inWishlist = isInWishlist(slug);
  const allergenTags = (detail?.dietary_tags ?? []).filter((tag) => tag.is_allergen);
  const dietaryTags = (detail?.dietary_tags ?? []).filter((tag) => !tag.is_allergen);
  const allergenText = detail?.allergen_note || (allergenTags.length ? `Contains: ${allergenTags.map((t) => t.name.replace(/^Contains\s+/i, "")).join(", ")}.` : "");
  const unavailableNow = detail ? !detail.is_available : false;

  const handleToggleWishlist = () => {
    if (inWishlist) {
      removeFromWishlist(slug);
      return;
    }
    addToWishlist({
      slug,
      name,
      description,
      price: price?.display ?? "",
      imageUrl: detail?.image_url ?? summary?.image_url ?? null,
    });
  };

  const handleShare = async () => {
    const url = `${window.location.origin}/menu?item=${encodeURIComponent(slug)}`;
    try {
      if (typeof navigator.share === "function") {
        await navigator.share({ title: name, url });
        return;
      }
      await navigator.clipboard.writeText(url);
      setShared(true);
      window.setTimeout(() => setShared(false), 2000);
    } catch {
      /* the customer dismissed the share sheet */
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogPortal>
        <DialogOverlay className="bg-black/70 supports-backdrop-filter:backdrop-blur-none" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed top-1/2 left-1/2 z-50 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl w-[calc(100%-2rem)] max-w-2xl max-h-[90vh] overflow-y-auto outline-none"
        >
          {/* Header Image */}
          <div className="relative h-64 sm:h-80" style={{ background: "var(--gray-light)" }}>
            {imageSrc ? (
              <Image src={imageSrc} alt={name} fill className="object-cover" sizes="(max-width: 672px) 100vw, 672px" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                {fallbackEmoji ? (
                  <span className="text-8xl" aria-hidden="true">{fallbackEmoji}</span>
                ) : (
                  <ShoppingCart className="w-24 h-24" style={{ color: "var(--text-muted)" }} />
                )}
              </div>
            )}

            {/* Close Button */}
            <DialogClose asChild>
              <button
                aria-label="Close"
                className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{ background: "rgba(255,255,255,0.9)" }}
              >
                <X className="w-6 h-6" style={{ color: "var(--black)" }} />
              </button>
            </DialogClose>

            {/* Actions */}
            <div className="absolute top-4 left-4 flex gap-2">
              <button
                onClick={handleToggleWishlist}
                aria-label={inWishlist ? "Remove from wishlist" : "Save to wishlist"}
                aria-pressed={inWishlist}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{ background: "rgba(255,255,255,0.9)" }}
              >
                <Heart
                  className={`w-5 h-5 ${inWishlist ? "fill-current" : ""}`}
                  style={{ color: inWishlist ? "var(--red)" : "var(--black)" }}
                />
              </button>
              <button
                onClick={handleShare}
                aria-label="Share this dish"
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                style={{ background: "rgba(255,255,255,0.9)" }}
              >
                {shared ? <Check className="w-5 h-5" style={{ color: "var(--red)" }} /> : <Share2 className="w-5 h-5" style={{ color: "var(--black)" }} />}
              </button>
              {shared && (
                <span className="self-center px-2 py-1 rounded-full text-xs font-bold" style={{ background: "rgba(255,255,255,0.9)", color: "var(--black)" }}>
                  Link copied
                </span>
              )}
            </div>
          </div>

          {/* Content */}
          <div className="p-6 sm:p-8">
            {/* Title & Description */}
            <div className="mb-6">
              <DialogTitle className="font-black text-2xl sm:text-3xl mb-2 leading-tight" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {name}
              </DialogTitle>
              <p className="text-sm sm:text-base mb-3" style={{ color: "var(--text-muted)" }}>
                {description}
              </p>
              {dietaryTags.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {dietaryTags.map((tag) => (
                    <span key={tag.slug} className="px-2 py-0.5 rounded-full text-xs font-semibold" style={{ background: "var(--gray-light)", color: "var(--black)" }}>
                      {tag.icon} {tag.name}
                    </span>
                  ))}
                </div>
              )}
              <p className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                {price?.display}
              </p>
            </div>

            {loadError && (
              <p role="alert" className="mb-6 text-sm font-semibold" style={{ color: "var(--red)" }}>
                {loadError}
              </p>
            )}

            {!detail && !loadError && (
              <div className="mb-6 flex items-center gap-2" role="status">
                <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
                <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading options…</span>
              </div>
            )}

            {/* Allergen Warning */}
            {allergenText && (
              <div className="mb-6 p-4 rounded-lg flex items-start gap-3" style={{ background: "#fef3c715", border: "1px solid #fef3c7" }}>
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "#f59e0b" }} />
                <div>
                  <p className="font-bold text-sm mb-1" style={{ color: "var(--black)" }}>Allergen Information</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{allergenText}</p>
                </div>
              </div>
            )}

            {detail && (
              <div className="space-y-6 mb-6">
                {/* Sizes */}
                {detail.variants.length > 0 && (
                  <fieldset>
                    <legend className="flex items-center gap-2 mb-3">
                      <span className="font-black text-lg" style={{ color: "var(--black)" }}>Portion Size</span>
                    </legend>
                    <div className="grid sm:grid-cols-2 gap-2">
                      {detail.variants.map((variant) => {
                        const isSelected = variantId === variant.id;
                        return (
                          <button
                            key={variant.id}
                            type="button"
                            role="radio"
                            aria-checked={isSelected}
                            onClick={() => setVariantId(variant.id)}
                            className="p-3 rounded-lg text-left transition-all"
                            style={{
                              background: isSelected ? "rgba(217,4,41,0.05)" : "var(--gray-light)",
                              border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}`,
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-sm" style={{ color: "var(--black)" }}>{variant.name}</span>
                              {variant.price_delta && variant.price_delta.amount !== 0 && (
                                <span className="text-xs font-bold" style={{ color: "var(--red)" }}>
                                  {variant.price_delta.amount > 0 ? "+" : ""}{variant.price_delta.display}
                                </span>
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </fieldset>
                )}

                {/* Options */}
                {groups.map((group) => {
                  const max = maximumFor(group);
                  const chosen = selected[group.id] ?? [];
                  const required = minimumFor(group) > 0;
                  const isMissing = missing.includes(group);
                  return (
                    <fieldset key={group.id}>
                      <legend className="flex items-center gap-2 mb-3">
                        <span className="font-black text-lg" style={{ color: "var(--black)" }}>{group.name}</span>
                        {required && (
                          <span className="px-2 py-0.5 rounded-full text-xs font-bold text-white" style={{ background: "var(--red)" }}>
                            Required
                          </span>
                        )}
                        {max > 1 && (
                          <span className="text-xs" style={{ color: "var(--text-muted)" }}>Choose up to {max}</span>
                        )}
                      </legend>
                      {group.description && (
                        <p className="text-xs -mt-2 mb-3" style={{ color: "var(--text-muted)" }}>{group.description}</p>
                      )}

                      <div className="grid sm:grid-cols-2 gap-2">
                        {group.modifiers.map((modifier) => {
                          const isSelected = chosen.includes(modifier.id);
                          const available = modifier.is_available !== false;
                          const atLimit = !isSelected && max > 1 && chosen.length >= max;
                          return (
                            <button
                              key={modifier.id}
                              type="button"
                              role={max <= 1 ? "radio" : "checkbox"}
                              aria-checked={isSelected}
                              disabled={!available || atLimit}
                              onClick={() => toggleModifier(group, modifier.id)}
                              className="p-3 rounded-lg text-left transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                              style={{
                                background: isSelected ? "rgba(217,4,41,0.05)" : "var(--gray-light)",
                                border: `2px solid ${isSelected ? "var(--red)" : "var(--gray-mid)"}`,
                              }}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-sm" style={{ color: "var(--black)" }}>
                                  {modifier.name}
                                  {!available && <span className="font-normal text-xs"> — unavailable</span>}
                                </span>
                                {modifier.price_delta && modifier.price_delta.amount > 0 && (
                                  <span className="text-xs font-bold" style={{ color: "var(--red)" }}>
                                    +{modifier.price_delta.display}
                                  </span>
                                )}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                      {isMissing && (
                        <p className="text-xs font-semibold mt-2" style={{ color: "var(--red)" }}>
                          Please choose {minimumFor(group) === 1 ? "an option" : `at least ${minimumFor(group)}`}.
                        </p>
                      )}
                    </fieldset>
                  );
                })}
              </div>
            )}

            {/* Special Instructions */}
            <div className="mb-6">
              <label htmlFor={`instructions-${slug}`} className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                Special Instructions (Optional)
              </label>
              <textarea
                id={`instructions-${slug}`}
                value={specialInstructions}
                onChange={(e) => setSpecialInstructions(e.target.value)}
                placeholder="Any special requests? (e.g., less spicy, extra sauce)"
                rows={3}
                maxLength={500}
                className="w-full px-4 py-3 rounded-lg border font-semibold resize-none"
                style={{ borderColor: "var(--gray-mid)" }}
              />
            </div>

            {unavailableNow && (
              <p className="mb-4 text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
                This dish isn&apos;t available right now.
              </p>
            )}

            {addError && (
              <p role="alert" className="mb-4 text-sm font-semibold" style={{ color: "var(--red)" }}>
                {addError}
              </p>
            )}

            {/* Quantity & Add to Cart */}
            <div className="flex items-center gap-4">
              {/* Quantity */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  aria-label="Decrease quantity"
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:opacity-80"
                  style={{ background: "var(--gray-light)", color: "var(--black)" }}
                >
                  <Minus className="w-4 h-4" />
                </button>
                <span className="font-black text-xl w-8 text-center" style={{ color: "var(--black)" }} aria-live="polite">
                  {quantity}
                </span>
                <button
                  type="button"
                  aria-label="Increase quantity"
                  onClick={() => setQuantity(Math.min(MAX_QUANTITY, quantity + 1))}
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:opacity-80"
                  style={{ background: "var(--red)", color: "white" }}
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>

              {/* Add to Cart */}
              <button
                type="button"
                onClick={handleAddToCart}
                disabled={!canConfigure || unavailableNow || addState !== "idle"}
                className="flex-1 px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-40"
                style={{ background: addState === "added" ? "var(--black)" : "var(--red)", color: "white" }}
              >
                {addState === "adding" ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : addState === "added" ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <ShoppingCart className="w-5 h-5" />
                )}
                {addState === "added"
                  ? "Added to Cart"
                  : canConfigure && quote
                    ? `Add to Cart • ${quote.line_total.display}`
                    : "Add to Cart"}
              </button>
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  );
}
