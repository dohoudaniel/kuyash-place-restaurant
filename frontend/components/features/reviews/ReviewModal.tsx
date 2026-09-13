"use client";

import { useEffect, useState } from "react";
import { X, Star, Loader2, CheckCircle } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Dialog, DialogClose, DialogOverlay, DialogPortal, DialogTitle } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api/client";
import { createReview, deleteReview, fetchOwnReview, updateReview } from "@/lib/api/reviews";
import type { OwnReview } from "@/lib/api/types";
import { formatDate } from "@/components/features/orders/statusStyles";

interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  itemName: string;
  /** Write a new review of this delivered order line… */
  orderLineId?: string;
  /** …or open the customer's existing review. */
  reviewId?: string;
  /** Called after a review is created, edited or deleted. Mount with a `key` per review target so each opens clean. */
  onSaved?: () => void;
}

const RATING_LABELS = ["", "Poor", "Fair", "Good", "Very Good", "Excellent!"];

const STATUS_NOTES: Record<OwnReview["status"], string> = {
  pending: "Awaiting approval. It will appear on the menu once our team has read it.",
  approved: "Published on the menu.",
  rejected: "Not published.",
};

/**
 * Write or edit a review of a dish the customer received.
 *
 * Previously this showed "It will be published after moderation", logged the
 * review to the console, and was mounted nowhere. Reviews now go to a real
 * moderation queue, tied to the order line they describe.
 */
export default function ReviewModal({ isOpen, onClose, itemName, orderLineId, reviewId, onSaved }: ReviewModalProps) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [title, setTitle] = useState("");
  const [comment, setComment] = useState("");
  const [recommends, setRecommends] = useState(true);
  const [existing, setExisting] = useState<OwnReview | null>(null);
  const [loading, setLoading] = useState(Boolean(reviewId));
  const [submitting, setSubmitting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<"saved" | "deleted" | null>(null);

  // Load the review being opened.
  useEffect(() => {
    if (!isOpen || !reviewId) return;
    let cancelled = false;
    fetchOwnReview(reviewId)
      .then((review) => {
        if (cancelled) return;
        setExisting(review);
        setRating(review.rating);
        setTitle(review.title);
        setComment(review.comment);
        setRecommends(review.recommends);
      })
      .catch(() => !cancelled && setError("We couldn't load your review. Please try again."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [isOpen, reviewId]);

  const editable = !existing || existing.can_edit;
  const shownRating = hoverRating || rating;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating === 0) {
      setError("Please select a star rating.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const input = { rating, title: title.trim(), comment: comment.trim(), recommends };
      if (existing) {
        await updateReview(existing.id, input);
      } else if (orderLineId) {
        await createReview(orderLineId, input);
      }
      setDone("saved");
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your review. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!existing) return;
    setSubmitting(true);
    setError(null);
    try {
      await deleteReview(existing.id);
      setDone("deleted");
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't delete your review. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogPortal>
        <DialogOverlay className="bg-black/70 supports-backdrop-filter:backdrop-blur-none" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed top-1/2 left-1/2 z-50 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl w-[calc(100%-2rem)] max-w-2xl max-h-[90vh] overflow-y-auto outline-none"
        >
          {/* Header */}
          <div className="sticky top-0 z-10 bg-white border-b px-6 sm:px-8 py-4 flex items-center justify-between" style={{ borderColor: "var(--gray-mid)" }}>
            <div>
              <DialogTitle className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {existing ? "Your Review" : "Write a Review"}
              </DialogTitle>
              <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                {itemName}
              </p>
            </div>
            <DialogClose asChild>
              <button aria-label="Close" className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100">
                <X className="w-6 h-6" style={{ color: "var(--black)" }} />
              </button>
            </DialogClose>
          </div>

          {done ? (
            <div className="p-6 sm:p-8 text-center" role="status">
              <CheckCircle className="w-12 h-12 mx-auto mb-4" style={{ color: "#10b981" }} />
              <p className="font-bold text-lg mb-2" style={{ color: "var(--black)" }}>
                {done === "deleted" ? "Your review has been deleted." : "Thank you for your review!"}
              </p>
              {done === "saved" && (
                <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
                  It will appear on the menu once our team has approved it.
                </p>
              )}
              <button
                type="button"
                onClick={onClose}
                className="mt-2 px-8 py-3 rounded-full font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Done
              </button>
            </div>
          ) : loading ? (
            <div className="p-6 sm:p-8 flex items-center gap-2" role="status">
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading your review…</span>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6">
              {existing && (
                <div className="p-4 rounded-lg" style={{ background: "var(--gray-light)" }}>
                  <p className="text-sm font-bold" style={{ color: "var(--black)" }}>{STATUS_NOTES[existing.status]}</p>
                  {existing.status === "rejected" && existing.rejection_reason && (
                    <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Reason: {existing.rejection_reason}</p>
                  )}
                  <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                    {existing.can_edit
                      ? `You can edit it until ${formatDate(existing.editable_until, "short")}. Edited reviews are checked again before they appear.`
                      : "The editing period for this review has ended."}
                  </p>
                </div>
              )}

              {/* Star Rating */}
              <fieldset disabled={!editable}>
                <legend className="block text-sm font-bold mb-3" style={{ color: "var(--black)" }}>
                  Overall Rating *
                </legend>
                <div className="flex items-center gap-2" onMouseLeave={() => setHoverRating(0)}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      role="radio"
                      aria-checked={rating === star}
                      aria-label={`${star} star${star > 1 ? "s" : ""}`}
                      onClick={() => setRating(star)}
                      onMouseEnter={() => setHoverRating(star)}
                      className="transition-transform hover:scale-110 disabled:hover:scale-100"
                    >
                      <Star
                        className={`w-10 h-10 transition-all ${star <= shownRating ? "fill-current" : ""}`}
                        style={{ color: star <= shownRating ? "var(--red)" : "var(--gray-mid)" }}
                      />
                    </button>
                  ))}
                  {shownRating > 0 && (
                    <span className="ml-3 text-lg font-bold" style={{ color: "var(--black)" }}>
                      {RATING_LABELS[shownRating]}
                    </span>
                  )}
                </div>
              </fieldset>

              {/* Review Title */}
              <div>
                <label htmlFor="review-title" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                  Review Title *
                </label>
                <input
                  id="review-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  disabled={!editable}
                  className="w-full px-4 py-3 rounded-lg border font-semibold disabled:opacity-60"
                  style={{ borderColor: "var(--gray-mid)" }}
                  placeholder="Sum up your experience in one line"
                  maxLength={100}
                />
              </div>

              {/* Review Comment */}
              <div>
                <label htmlFor="review-comment" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                  Your Review *
                </label>
                <textarea
                  id="review-comment"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  required
                  disabled={!editable}
                  rows={6}
                  className="w-full px-4 py-3 rounded-lg border font-semibold resize-none disabled:opacity-60"
                  style={{ borderColor: "var(--gray-mid)" }}
                  placeholder="Share details about your experience. What did you like or dislike?"
                  maxLength={1000}
                />
                <div className="text-xs mt-1 text-right" style={{ color: "var(--text-muted)" }}>
                  {comment.length}/1000 characters
                </div>
              </div>

              {/* Recommend */}
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="review-recommends"
                  checked={recommends}
                  onChange={(e) => setRecommends(e.target.checked)}
                  disabled={!editable}
                  className="mt-1"
                />
                <label htmlFor="review-recommends" className="text-sm cursor-pointer" style={{ color: "var(--black)" }}>
                  I would recommend this dish to others
                </label>
              </div>

              {/* Guidelines */}
              {editable && (
                <div className="p-4 rounded-lg" style={{ background: "#fef3c715", border: "1px solid #fef3c7" }}>
                  <p className="text-xs font-bold mb-2" style={{ color: "var(--black)" }}>
                    Review Guidelines
                  </p>
                  <ul className="text-xs space-y-1" style={{ color: "var(--text-muted)" }}>
                    <li>• Be honest and respectful</li>
                    <li>• Focus on your personal experience</li>
                    <li>• Avoid offensive language or personal attacks</li>
                    <li>• Reviews are moderated and appear once approved</li>
                    <li>• Only your first name and last initial are shown</li>
                  </ul>
                </div>
              )}

              {error && (
                <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>
                  {error}
                </p>
              )}

              {/* Actions */}
              {confirmDelete ? (
                <div className="p-3 rounded-lg" style={{ background: "var(--off-white)" }}>
                  <p className="text-sm mb-2" style={{ color: "var(--black)" }}>Delete this review? This can&apos;t be undone.</p>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setConfirmDelete(false)} className="flex-1 py-2 rounded-lg text-sm font-semibold" style={{ border: "2px solid var(--gray-mid)" }}>
                      Keep Review
                    </button>
                    <button type="button" onClick={handleDelete} disabled={submitting} className="flex-1 py-2 rounded-lg text-sm font-bold text-white disabled:opacity-50" style={{ background: "var(--red)" }}>
                      {submitting ? "Deleting..." : "Yes, Delete"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-4 pt-4">
                  {existing ? (
                    <button
                      type="button"
                      onClick={() => setConfirmDelete(true)}
                      className="flex-1 py-3 rounded-full font-bold transition-all hover:opacity-80"
                      style={{ background: "var(--gray-light)", color: "var(--red)" }}
                    >
                      Delete Review
                    </button>
                  ) : (
                    <DialogClose asChild>
                      <button
                        type="button"
                        className="flex-1 py-3 rounded-full font-bold transition-all hover:opacity-80"
                        style={{ background: "var(--gray-light)", color: "var(--black)" }}
                      >
                        Cancel
                      </button>
                    </DialogClose>
                  )}
                  {editable && (
                    <button
                      type="submit"
                      disabled={submitting}
                      className="flex-1 py-3 rounded-full font-bold text-white flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
                      style={{ background: "var(--red)" }}
                    >
                      {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                      {existing ? "Save Changes" : "Submit Review"}
                    </button>
                  )}
                </div>
              )}
            </form>
          )}
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  );
}
