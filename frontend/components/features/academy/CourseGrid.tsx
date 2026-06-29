"use client";

import { Star, Clock, Users, CheckCircle, BookOpen } from "lucide-react";
import type { Course } from "@/app/academy/page";

interface CourseGridProps {
  courses: Course[];
  onEnroll: (course: Course) => void;
}

export default function CourseGrid({ courses, onEnroll }: CourseGridProps) {
  if (courses.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lg font-bold" style={{ color: "var(--text-muted)" }}>
          No courses found. Try adjusting your filters.
        </p>
      </div>
    );
  }

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
      {courses.map((course) => (
        <div
          key={course.id}
          className="bg-white rounded-xl border overflow-hidden transition-all hover:shadow-xl hover:-translate-y-1"
          style={{ borderColor: "var(--gray-mid)" }}
        >
          {/* Image */}
          <div className="h-48 flex items-center justify-center" style={{ background: "var(--gray-light)" }}>
            <BookOpen className="w-16 h-16" style={{ color: "var(--text-muted)" }} />
          </div>

          {/* Content */}
          <div className="p-5">
            {/* Category Badge */}
            <div className="flex items-center justify-between mb-3">
              <span
                className="px-3 py-1 rounded-full text-xs font-bold text-white capitalize"
                style={{ background: "var(--red)" }}
              >
                {course.category}
              </span>
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                <span className="text-sm font-bold" style={{ color: "var(--black)" }}>
                  {course.rating}
                </span>
              </div>
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
              by {course.instructor}
            </p>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-2 mb-4">
              <div className="flex items-center gap-2 p-2 rounded-lg" style={{ background: "var(--gray-light)" }}>
                <Clock className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
                <div>
                  <p className="text-xs font-bold" style={{ color: "var(--black)" }}>{course.duration}</p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{course.sessions} sessions</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg" style={{ background: "var(--gray-light)" }}>
                <Users className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
                <div>
                  <p className="text-xs font-bold" style={{ color: "var(--black)" }}>{course.students}</p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>students</p>
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
                  ₦{course.price.toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => onEnroll(course)}
                className="px-5 py-2.5 rounded-lg font-bold text-sm transition-all hover:opacity-90"
                style={{ background: "var(--red)", color: "white" }}
              >
                Enroll Now
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
