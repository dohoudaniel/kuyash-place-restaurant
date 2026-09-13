const STAR_PATH =
  "M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z";

interface StarRatingProps {
  /** The API's decimal string, e.g. "4.60", or null when unrated. */
  rating: string | null | undefined;
  count?: number;
  starClassName?: string;
}

/**
 * Real ratings from approved reviews. Previously every dish showed five stars
 * and "5.0" regardless of whether anyone had reviewed it.
 */
export default function StarRating({ rating, count = 0, starClassName = "w-3.5 h-3.5" }: StarRatingProps) {
  const value = rating ? Number(rating) : 0;
  const hasReviews = count > 0 && value > 0;
  const filled = hasReviews ? Math.round(value) : 0;

  return (
    <div className="flex items-center gap-1" aria-label={hasReviews ? `Rated ${value.toFixed(1)} out of 5` : "No reviews yet"}>
      {[...Array(5)].map((_, i) => (
        <svg key={i} className={starClassName} viewBox="0 0 20 20" fill={i < filled ? "var(--red)" : "var(--gray-mid)"} aria-hidden="true">
          <path d={STAR_PATH} />
        </svg>
      ))}
      <span className="text-xs ml-1" style={{ color: "var(--text-muted)" }}>
        {hasReviews ? `${value.toFixed(1)} (${count})` : "No reviews yet"}
      </span>
    </div>
  );
}
