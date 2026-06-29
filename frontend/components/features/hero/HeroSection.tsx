"use client";

import Navbar from "@/components/layouts/navbar";
import HeroContent from "./HeroContent";
import HeroStats from "./HeroStats";
import HeroImage from "./HeroImage";

export default function HeroSection() {
  return (
    <section
      className="relative min-h-screen overflow-hidden"
      style={{ background: "var(--white)" }}
    >
      {/* Faint decorative circle watermarks */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute rounded-full hidden md:block" style={{ width: "clamp(300px, 40vw, 520px)", height: "clamp(300px, 40vw, 520px)", top: "5%", left: "20%", border: "1.5px solid rgba(217,4,41,0.08)" }} />
        <div className="absolute rounded-full hidden md:block" style={{ width: "clamp(200px, 28vw, 360px)", height: "clamp(200px, 28vw, 360px)", top: "18%", left: "30%", border: "1.5px solid rgba(217,4,41,0.05)" }} />
        <div className="absolute rounded-full" style={{ width: "clamp(120px, 18vw, 200px)", height: "clamp(120px, 18vw, 200px)", top: "8%", left: "8%", border: "1.5px solid rgba(217,4,41,0.05)" }} />
      </div>

      <Navbar />

      {/* Hero content */}
      <div className="relative z-10 flex flex-col lg:flex-row items-center lg:items-stretch min-h-screen pt-28 sm:pt-32 md:pt-36 lg:pt-32">
        {/* ── Left panel ── */}
        <div className="flex-1 flex flex-col justify-between px-4 sm:px-6 md:px-12 lg:px-16 xl:px-20 py-8 sm:py-10 lg:py-0 lg:min-h-screen w-full lg:w-auto lg:max-w-[55%]">
          <HeroContent />
          <HeroStats />
        </div>

        {/* ── Right panel ── */}
        <HeroImage />
      </div>
    </section>
  );
}
