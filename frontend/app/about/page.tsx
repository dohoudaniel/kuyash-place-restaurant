"use client";

import AboutHero from "@/components/features/about/AboutHero";
import StorySection from "@/components/features/about/StorySection";
import TeamSection from "@/components/features/about/TeamSection";
import ValuesSection from "@/components/features/about/ValuesSection";
import AchievementsSection from "@/components/features/about/AchievementsSection";

export default function AboutPage() {
  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <AboutHero />
      <div className="container-custom py-6 sm:py-8 space-y-8 sm:space-y-12">
        <StorySection />
        <ValuesSection />
        <TeamSection />
        <AchievementsSection />
      </div>
    </div>
  );
}
