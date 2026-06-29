"use client";

import { useState } from "react";
import AcademyHero from "@/components/features/academy/AcademyHero";
import CourseFilters from "@/components/features/academy/CourseFilters";
import CourseGrid from "@/components/features/academy/CourseGrid";
import EnrollmentModal from "@/components/features/academy/EnrollmentModal";

export type CourseCategory = "all" | "beginner" | "intermediate" | "advanced" | "masterclass";
export type CourseType = "cooking" | "baking" | "plating" | "business" | "nutrition";

export interface Course {
  id: string;
  title: string;
  description: string;
  instructor: string;
  category: CourseCategory;
  type: CourseType;
  duration: string;
  sessions: number;
  price: number;
  rating: number;
  students: number;
  features: string[];
  imageKey: string;
}

const COURSES: Course[] = [
  {
    id: "1",
    title: "Nigerian Cuisine Fundamentals",
    description: "Master the basics of traditional Nigerian cooking",
    instructor: "Chef Emmanuel Kuyash",
    category: "beginner",
    type: "cooking",
    duration: "4 weeks",
    sessions: 8,
    price: 50000,
    rating: 4.9,
    students: 234,
    features: ["Hands-on Practice", "Recipe Book", "Certificate"],
    imageKey: "nigerian-basics",
  },
  {
    id: "2",
    title: "Advanced Pastry & Baking",
    description: "Professional techniques for breads, cakes, and pastries",
    instructor: "Chef David Adeleke",
    category: "advanced",
    type: "baking",
    duration: "6 weeks",
    sessions: 12,
    price: 75000,
    rating: 5.0,
    students: 156,
    features: ["Small Class", "Equipment Included", "Certificate"],
    imageKey: "pastry",
  },
  {
    id: "3",
    title: "Restaurant Plating & Presentation",
    description: "Learn the art of beautiful food presentation",
    instructor: "Chef Sarah Okonkwo",
    category: "intermediate",
    type: "plating",
    duration: "3 weeks",
    sessions: 6,
    price: 40000,
    rating: 4.8,
    students: 189,
    features: ["Photography Tips", "Portfolio Building", "Certificate"],
    imageKey: "plating",
  },
  {
    id: "4",
    title: "Restaurant Business Management",
    description: "Everything you need to start and run a restaurant",
    instructor: "Grace Nnamdi",
    category: "intermediate",
    type: "business",
    duration: "5 weeks",
    sessions: 10,
    price: 60000,
    rating: 4.7,
    students: 98,
    features: ["Business Plan Template", "Mentorship", "Certificate"],
    imageKey: "business",
  },
  {
    id: "5",
    title: "Nutrition & Menu Planning",
    description: "Create balanced, healthy menus that taste great",
    instructor: "Dr. Amina Ibrahim",
    category: "intermediate",
    type: "nutrition",
    duration: "4 weeks",
    sessions: 8,
    price: 45000,
    rating: 4.9,
    students: 167,
    features: ["Meal Plans", "Nutrition Charts", "Certificate"],
    imageKey: "nutrition",
  },
  {
    id: "6",
    title: "Culinary Masterclass",
    description: "Exclusive intensive with Chef Emmanuel",
    instructor: "Chef Emmanuel Kuyash",
    category: "masterclass",
    type: "cooking",
    duration: "2 weeks",
    sessions: 10,
    price: 150000,
    rating: 5.0,
    students: 45,
    features: ["1-on-1 Sessions", "Premium Ingredients", "Master Certificate"],
    imageKey: "masterclass",
  },
];

export default function AcademyPage() {
  const [selectedCategory, setSelectedCategory] = useState<CourseCategory>("all");
  const [selectedType, setSelectedType] = useState<CourseType | "all">("all");
  const [enrollCourse, setEnrollCourse] = useState<Course | null>(null);

  const filteredCourses = COURSES.filter((course) => {
    const matchesCategory = selectedCategory === "all" || course.category === selectedCategory;
    const matchesType = selectedType === "all" || course.type === selectedType;
    return matchesCategory && matchesType;
  });

  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <AcademyHero totalCourses={COURSES.length} />

      <div className="container-custom py-6 sm:py-8">
        <CourseFilters
          selectedCategory={selectedCategory}
          selectedType={selectedType}
          onSelectCategory={setSelectedCategory}
          onSelectType={setSelectedType}
        />
        <CourseGrid courses={filteredCourses} onEnroll={setEnrollCourse} />
      </div>

      {enrollCourse && <EnrollmentModal course={enrollCourse} onClose={() => setEnrollCourse(null)} />}
    </div>
  );
}
