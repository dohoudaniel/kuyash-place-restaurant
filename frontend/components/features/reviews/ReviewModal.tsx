"use client";

import { useState } from "react";
import { X, Star } from "lucide-react";

interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  itemName: string;
  itemType: "menu" | "restaurant" | "service";
  onSubmit?: (review: ReviewData) => void;
}

export interface ReviewData {
  rating: number;
  title: string;
  comment: string;
  recommend: boolean;
  name: string;
  email: string;
}

export default function ReviewModal({ isOpen, onClose, itemName, itemType, onSubmit }: ReviewModalProps) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [formData, setFormData] = useState<ReviewData>({
    rating: 0,
    title: "",
    comment: "",
    recommend: true,
    name: "",
    email: "",
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (rating === 0) {
      alert("Please select a star rating");
      return;
    }

    const reviewData = { ...formData, rating };

    if (onSubmit) {
      onSubmit(reviewData);
    } else {
      alert("Thank you for your review! It will be published after moderation.");
      console.log("Review submitted:", reviewData);
    }

    onClose();
    // Reset form
    setRating(0);
    setFormData({
      rating: 0,
      title: "",
      comment: "",
      recommend: true,
      name: "",
      email: "",
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData({
      ...formData,
      [name]: type === "checkbox" ? (e.target as HTMLInputElement).checked : value,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.7)" }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 sm:px-8 py-4 flex items-center justify-between" style={{ borderColor: "var(--gray-mid)" }}>
          <div>
            <h2 className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Write a Review
            </h2>
            <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
              {itemName}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:bg-gray-100"
          >
            <X className="w-6 h-6" style={{ color: "var(--black)" }} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6">
          {/* Star Rating */}
          <div>
            <label className="block text-sm font-bold mb-3" style={{ color: "var(--black)" }}>
              Overall Rating *
            </label>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="transition-transform hover:scale-110"
                >
                  <Star
                    className={`w-10 h-10 transition-all ${
                      star <= (hoverRating || rating) ? "fill-current" : ""
                    }`}
                    style={{
                      color: star <= (hoverRating || rating) ? "var(--red)" : "var(--gray-mid)",
                    }}
                  />
                </button>
              ))}
              {rating > 0 && (
                <span className="ml-3 text-lg font-bold" style={{ color: "var(--black)" }}>
                  {rating === 5
                    ? "Excellent!"
                    : rating === 4
                    ? "Very Good"
                    : rating === 3
                    ? "Good"
                    : rating === 2
                    ? "Fair"
                    : "Poor"}
                </span>
              )}
            </div>
          </div>

          {/* Review Title */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Review Title *
            </label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
              placeholder="Sum up your experience in one line"
              maxLength={100}
            />
          </div>

          {/* Review Comment */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Your Review *
            </label>
            <textarea
              name="comment"
              value={formData.comment}
              onChange={handleChange}
              required
              rows={6}
              className="w-full px-4 py-3 rounded-lg border font-semibold resize-none"
              style={{ borderColor: "var(--gray-mid)" }}
              placeholder="Share details about your experience. What did you like or dislike?"
              maxLength={1000}
            />
            <div className="text-xs mt-1 text-right" style={{ color: "var(--text-muted)" }}>
              {formData.comment.length}/1000 characters
            </div>
          </div>

          {/* Recommend */}
          <div className="flex items-start gap-3">
            <input
              type="checkbox"
              name="recommend"
              id="recommend"
              checked={formData.recommend}
              onChange={handleChange}
              className="mt-1"
            />
            <label htmlFor="recommend" className="text-sm cursor-pointer" style={{ color: "var(--black)" }}>
              I would recommend this {itemType === "menu" ? "dish" : itemType} to others
            </label>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Your Name *
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
              placeholder="John Doe"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Email Address *
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
              placeholder="john@example.com"
            />
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Your email won't be publicly displayed
            </p>
          </div>

          {/* Guidelines */}
          <div className="p-4 rounded-lg" style={{ background: "#fef3c715", border: "1px solid #fef3c7" }}>
            <p className="text-xs font-bold mb-2" style={{ color: "var(--black)" }}>
              Review Guidelines
            </p>
            <ul className="text-xs space-y-1" style={{ color: "var(--text-muted)" }}>
              <li>• Be honest and respectful</li>
              <li>• Focus on your personal experience</li>
              <li>• Avoid offensive language or personal attacks</li>
              <li>• Reviews are moderated and may take 24-48 hours to appear</li>
            </ul>
          </div>

          {/* Submit Button */}
          <div className="flex gap-4 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 rounded-full font-bold transition-all hover:opacity-80"
              style={{ background: "var(--gray-light)", color: "var(--black)" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 py-3 rounded-full font-bold text-white transition-all hover:opacity-90"
              style={{ background: "var(--red)" }}
            >
              Submit Review
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
