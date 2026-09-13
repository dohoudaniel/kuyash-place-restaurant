"use client";

import { useEffect, useState } from "react";
import { Star, ThumbsUp, BadgeCheck, Loader2 } from "lucide-react";
import StarRating from "@/components/features/menu/StarRating";
import { formatDate } from "@/components/features/orders/statusStyles";
import { ApiError } from "@/lib/api/client";
import { fetchReviews, markHelpful, type ReviewSort } from "@/lib/api/reviews";
import type { Review } from "@/lib/api/types";

interface ReviewListProps {
  slug: string;
  averageRating: string | null | undefined;
  reviewCount: number;
}

const SORT_LABELS: Record<ReviewSort, string> = {
  newest: "Newest",
  helpful: "Most helpful",
  highest: "Highest rated",
  lowest: "Lowest rated",
};

/**
 * A dish's published reviews. Only reviews a manager has approved reach this
 * list, and each one comes from someone who received the dish.
 */
export default function ReviewList({ slug, averageRating, reviewCount }: ReviewListProps) {
  const [sort, setSort] = useState<ReviewSort>("newest");
  const [reviews, setReviews] = useState<Review[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [voted, setVoted] = useState<Record<string, boolean>>({});

  const requestKey = `${slug}|${sort}|${page}`;
  const loading = reviewCount > 0 && loadedKey !== requestKey;

  useEffect(() => {
    if (reviewCount === 0) return;
    let cancelled = false;
    fetchReviews(slug, { sort, page })
      .then((data) => {
        if (cancelled) return;
        setReviews((current) => (page === 1 ? data.results : [...current, ...data.results]));
        setHasMore(Boolean(data.next));
        setError(null);
        setLoadedKey(`${slug}|${sort}|${page}`);
      })
      .catch(() => {
        if (cancelled) return;
        setError("We couldn't load reviews right now.");
        setLoadedKey(`${slug}|${sort}|${page}`);
      });
    return () => {
      cancelled = true;
    };
  }, [slug, sort, page, reviewCount]);

  const changeSort = (next: ReviewSort) => {
    setSort(next);
    setPage(1);
  };

  const vote = async (review: Review) => {
    setVoted((current) => ({ ...current, [review.id]: true }));
    try {
      const result = await markHelpful(review.id);
      setReviews((current) => current.map((row) => (row.id === review.id ? { ...row, helpful_count: result.helpful_count } : row)));
    } catch (err) {
      // Your own review can't be voted on; leave the button as it was for anything else.
      if (!(err instanceof ApiError && err.code === "own_review")) {
        setVoted((current) => ({ ...current, [review.id]: false }));
      }
    }
  };

  return (
    <section aria-labelledby={`reviews-${slug}`} className="mt-8 pt-6 border-t" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h3 id={`reviews-${slug}`} className="font-black text-lg" style={{ color: "var(--black)" }}>
            Reviews
          </h3>
          <StarRating rating={averageRating} count={reviewCount} starClassName="w-4 h-4" />
        </div>
        {reviewCount > 1 && (
          <label className="text-xs font-semibold flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
            Sort
            <select
              value={sort}
              onChange={(e) => changeSort(e.target.value as ReviewSort)}
              className="px-3 py-1.5 rounded-lg border text-xs font-semibold bg-white"
              style={{ borderColor: "var(--gray-mid)", color: "var(--black)" }}
            >
              {(Object.keys(SORT_LABELS) as ReviewSort[]).map((key) => (
                <option key={key} value={key}>{SORT_LABELS[key]}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      {reviewCount === 0 && (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          No reviews yet. Customers can review this dish once their order has been delivered.
        </p>
      )}

      {error && (
        <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>{error}</p>
      )}

      <ul className="space-y-4">
        {reviews.map((review) => (
          <li key={review.id} className="p-4 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-0.5" aria-label={`Rated ${review.rating} out of 5`}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star
                    key={star}
                    aria-hidden="true"
                    className={`w-4 h-4 ${star <= review.rating ? "fill-current" : ""}`}
                    style={{ color: star <= review.rating ? "var(--red)" : "var(--gray-mid)" }}
                  />
                ))}
              </div>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>{formatDate(review.created_at, "short")}</span>
            </div>
            <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{review.title}</p>
            <p className="text-sm mt-1 whitespace-pre-line" style={{ color: "var(--black)" }}>{review.comment}</p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
              <span className="font-semibold">{review.author_name}</span>
              {review.is_verified_purchase && (
                <span className="flex items-center gap-1 font-semibold">
                  <BadgeCheck className="w-3.5 h-3.5" style={{ color: "#10b981" }} />
                  Verified purchase
                </span>
              )}
              {review.recommends && <span>Recommends this dish</span>}
              <button
                type="button"
                onClick={() => vote(review)}
                disabled={voted[review.id]}
                aria-pressed={voted[review.id] ?? false}
                className="ml-auto flex items-center gap-1 px-2 py-1 rounded-full font-semibold transition-all hover:opacity-80 disabled:opacity-60"
                style={{ background: "white", color: "var(--black)" }}
              >
                <ThumbsUp className="w-3.5 h-3.5" />
                Helpful{review.helpful_count > 0 ? ` (${review.helpful_count})` : ""}
              </button>
            </div>
          </li>
        ))}
      </ul>

      {loading && (
        <div className="mt-4 flex items-center gap-2" role="status">
          <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--red)" }} />
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading reviews…</span>
        </div>
      )}

      {hasMore && !loading && (
        <button
          type="button"
          onClick={() => setPage((current) => current + 1)}
          className="mt-4 w-full py-2.5 rounded-full text-sm font-bold transition-all hover:opacity-80"
          style={{ background: "var(--gray-light)", color: "var(--black)" }}
        >
          Show more reviews
        </button>
      )}
    </section>
  );
}
