"use client";

import { Heart, Award, Leaf, Users, Clock, Shield } from "lucide-react";

export default function ValuesSection() {
  const values = [
    {
      icon: Heart,
      title: "Passion",
      description: "Every dish is prepared with love and dedication to culinary excellence",
      color: "var(--red)",
    },
    {
      icon: Award,
      title: "Quality",
      description: "We source only the finest ingredients and maintain the highest standards",
      color: "#f59e0b",
    },
    {
      icon: Leaf,
      title: "Sustainability",
      description: "Committed to eco-friendly practices and supporting local farmers",
      color: "#10b981",
    },
    {
      icon: Users,
      title: "Community",
      description: "Building connections through food and creating memorable experiences",
      color: "#3b82f6",
    },
    {
      icon: Clock,
      title: "Tradition",
      description: "Honoring time-tested recipes while embracing innovation",
      color: "#8b5cf6",
    },
    {
      icon: Shield,
      title: "Integrity",
      description: "Transparent operations and authentic relationships with our guests",
      color: "#ec4899",
    },
  ];

  return (
    <div>
      <div className="text-center mb-6">
        <h2 className="font-black text-2xl sm:text-3xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Our Values
        </h2>
        <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
          The principles that guide everything we do
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {values.map((value, idx) => {
          const Icon = value.icon;
          return (
            <div
              key={idx}
              className="bg-white rounded-xl border p-5 transition-all hover:shadow-lg hover:-translate-y-1"
              style={{ borderColor: "var(--gray-mid)" }}
            >
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center mb-3"
                style={{ background: `${value.color}15` }}
              >
                <Icon className="w-6 h-6" style={{ color: value.color }} />
              </div>
              <h3 className="font-black text-lg mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {value.title}
              </h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                {value.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
