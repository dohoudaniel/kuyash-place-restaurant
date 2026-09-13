"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import AcademyHero from "@/components/features/academy/AcademyHero";
import CourseFilters, { type LevelFilter, type TypeFilter } from "@/components/features/academy/CourseFilters";
import CourseGrid from "@/components/features/academy/CourseGrid";
import EnrollmentModal from "@/components/features/academy/EnrollmentModal";
import { fetchCourses } from "@/lib/api/academy";
import type { Course } from "@/lib/api/types";

export default function AcademyPage() {
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<LevelFilter>("all");
  const [selectedType, setSelectedType] = useState<TypeFilter>("all");
  const [enrollCourse, setEnrollCourse] = useState<Course | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCourses()
      .then((data) => !cancelled && setCourses(data))
      .catch(() => !cancelled && setLoadError(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const all = courses ?? [];
  const filteredCourses = all.filter((course) => {
    const matchesCategory = selectedCategory === "all" || course.level === selectedCategory;
    const matchesType = selectedType === "all" || course.type === selectedType;
    return matchesCategory && matchesType;
  });

  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <AcademyHero courses={all} />

      <div className="container-custom py-6 sm:py-8">
        <CourseFilters
          selectedCategory={selectedCategory}
          selectedType={selectedType}
          onSelectCategory={setSelectedCategory}
          onSelectType={setSelectedType}
        />
        {loadError ? (
          <p role="alert" className="text-center py-12 text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
            We couldn&apos;t load our courses. Please check your connection and try again.
          </p>
        ) : courses === null ? (
          <div className="flex justify-center py-12" role="status" aria-label="Loading courses">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
          </div>
        ) : (
          <CourseGrid courses={filteredCourses} hasAny={all.length > 0} onEnroll={setEnrollCourse} />
        )}
      </div>

      {enrollCourse && <EnrollmentModal key={enrollCourse.slug} course={enrollCourse} onClose={() => setEnrollCourse(null)} />}
    </div>
  );
}
