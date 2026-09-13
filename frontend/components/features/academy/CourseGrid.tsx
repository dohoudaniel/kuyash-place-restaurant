"use client";

import Image from "next/image";
import { Calendar, Clock, Users, CheckCircle, BookOpen } from "lucide-react";
import { formatDate } from "@/components/features/orders/statusStyles";
import { mediaUrl } from "@/lib/api/media";
import type { Course } from "@/lib/api/types";

interface CourseGridProps {
  courses: Course[];
  /** Whether any course is published at all, to tell "none match" from "none yet". */
  hasAny: boolean;
  onEnroll: (course: Course) => void;
}

export default function CourseGrid({ courses, hasAny, onEnroll }: CourseGridProps) {
  if (courses.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-bold" style={{ color: "var(--text-muted)" }}>
          {hasAny ? "No courses found. Try adjusting your filters." : "New courses are on the way. Check back soon."}
        </p>
      </div>
    );
  }

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
      {courses.map((course) => {
        const thumbnail = mediaUrl(course.thumbnail_url);
        const next = course.next_cohort;
        const canEnroll = Boolean(next && next.seats_left > 0);
        return (
          <div
            key={course.slug}
            className="bg-white rounded-xl border overflow-hidden transition-all hover:shadow-xl hover:-translate-y-1"
            style={{ borderColor: "var(--gray-mid)" }}
          >
            {/* Image */}
            <div className="relative h-48 flex items-center justify-center" style={{ background: "var(--gray-light)" }}>
              {thumbnail ? (
                <Image src={thumbnail} alt={course.title} fill sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw" className="object-cover" />
              ) : (
                <BookOpen className="w-16 h-16" style={{ color: "var(--text-muted)" }} />
              )}
            </div>

            {/* Content */}
            <div className="p-5">
              {/* Category Badge */}
              <div className="flex items-center justify-between mb-3">
                <span
                  className="px-3 py-1 rounded-full text-xs font-bold text-white capitalize"
                  style={{ background: "var(--red)" }}
                >
                  {course.level_display}
                </span>
                {next && (
                  <div className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
                    <span className="text-xs font-bold" style={{ color: "var(--black)" }}>
                      Starts {formatDate(next.starts_on, "short")}
                    </span>
                  </div>
                )}
              </div>

              {/* Title */}
              <h3 className="font-black text-lg mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {course.title}
              </h3>

              {/* Description */}
              <p className="text-sm mb-3 line-clamp-2" style={{ color: "var(--text-muted)" }}>
                {course.description}
              </p>

              {/* Instructor */}
              <p className="text-xs font-bold mb-3" style={{ color: "var(--red)" }}>
                by {course.instructor.name}
              </p>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-2 mb-4">
                <div className="flex items-center gap-2 p-2 rounded-lg" style={{ background: "var(--gray-light)" }}>
                  <Clock className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
                  <div>
                    <p className="text-xs font-bold" style={{ color: "var(--black)" }}>{course.duration_label}</p>
                    <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{course.session_count} sessions</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-lg" style={{ background: "var(--gray-light)" }}>
                  <Users className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
                  <div>
                    <p className="text-xs font-bold" style={{ color: "var(--black)" }}>
                      {next ? (next.seats_left > 0 ? `${next.seats_left} seats left` : "Class full") : "Dates TBA"}
                    </p>
                    <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                      {course.student_count > 0 ? `${course.student_count} students` : "next class"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Features */}
              <div className="space-y-1 mb-4">
                {course.features.slice(0, 3).map((feature) => (
                  <div key={feature} className="flex items-center gap-2">
                    <CheckCircle className="w-3 h-3" style={{ color: "#10b981" }} />
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>{feature}</p>
                  </div>
                ))}
              </div>

              {/* Price & Enroll */}
              <div className="flex items-center justify-between pt-4" style={{ borderTop: "1px solid var(--gray-mid)" }}>
                <div>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>Price</p>
                  <p className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                    {course.price.display}
                  </p>
                </div>
                <button
                  onClick={() => onEnroll(course)}
                  disabled={!canEnroll}
                  className="px-5 py-2.5 rounded-lg font-bold text-sm transition-all hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: "var(--red)", color: "white" }}
                >
                  {canEnroll ? "Enroll Now" : next ? "Class Full" : "Dates Coming Soon"}
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
