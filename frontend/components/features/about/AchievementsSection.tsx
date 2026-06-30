"use client";

import { Trophy, Star, Award, Medal, Crown, Zap } from "lucide-react";

export default function AchievementsSection() {
  const achievements = [
    { icon: Trophy, title: "Best Restaurant 2024", org: "Lagos Food Awards", color: "#f59e0b" },
    { icon: Star, title: "Michelin Guide Featured", org: "Michelin Guide", color: "var(--red)" },
    { icon: Award, title: "5-Star Rating", org: "TripAdvisor Excellence", color: "#10b981" },
    { icon: Medal, title: "Top 10 in Nigeria", org: "National Dining Awards", color: "#3b82f6" },
    { icon: Crown, title: "Chef of the Year", org: "Culinary Institute", color: "#8b5cf6" },
    { icon: Zap, title: "Innovation Award", org: "Restaurant Tech Summit", color: "#ec4899" },
  ];

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="text-center mb-6">
        <h2 className="font-black text-2xl sm:text-3xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Awards & Recognition
        </h2>
        <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
          Celebrating excellence in culinary arts and service
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {achievements.map((achievement, idx) => {
          const Icon = achievement.icon;
          return (
            <div
              key={idx}
              className="flex flex-col items-center text-center p-4 rounded-xl transition-all hover:shadow-lg hover:-translate-y-1"
              style={{ background: `${achievement.color}08`, border: `1px solid ${achievement.color}30` }}
            >
              <div
                className="w-14 h-14 rounded-full flex items-center justify-center mb-3"
                style={{ background: `${achievement.color}20` }}
              >
                <Icon className="w-7 h-7" style={{ color: achievement.color }} />
              </div>
              <h4 className="font-black text-xs sm:text-sm mb-1" style={{ color: "var(--black)" }}>
                {achievement.title}
              </h4>
              <p className="text-[10px] sm:text-xs" style={{ color: "var(--text-muted)" }}>
                {achievement.org}
              </p>
            </div>
          );
        })}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mt-8 pt-6" style={{ borderTop: "1px solid var(--gray-mid)" }}>
        {[
          { value: "100k+", label: "Happy Guests" },
          { value: "500+", label: "Events Hosted" },
          { value: "18", label: "Menu Items" },
          { value: "9.5/10", label: "Avg Rating" },
        ].map((stat, idx) => (
          <div key={idx} className="text-center">
            <p className="font-black text-xl sm:text-2xl mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
              {stat.value}
            </p>
            <p className="text-xs font-bold" style={{ color: "var(--text-muted)" }}>
              {stat.label}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
