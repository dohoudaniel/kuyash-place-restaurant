"use client";

import Navbar from "@/components/layouts/navbar";
import HeroContent from "./HeroContent";
import HeroStats from "./HeroStats";

export default function HeroSection() {
  return (
    <section
      className="relative overflow-hidden"
      style={{ background: "#0d0d0d", height: "100vh" }}
    >
      {/* Decorative red circle rings */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute rounded-full hidden lg:block"
          style={{
            width: "520px",
            height: "520px",
            top: "55%",
            left: "27%",
            transform: "translate(-50%, -50%)",
            border: "1px solid rgba(217,4,41,0.15)",
          }}
        />
        <div
          className="absolute rounded-full hidden lg:block"
          style={{
            width: "360px",
            height: "360px",
            top: "55%",
            left: "27%",
            transform: "translate(-50%, -50%)",
            border: "1px solid rgba(217,4,41,0.10)",
          }}
        />
      </div>

      {/* Navbar fixed at top */}
      <Navbar />

      {/* Content row — starts BELOW navbar via pt-24 */}
      <div className="flex flex-row h-full pt-24">

        {/* Left panel */}
        <div className="flex flex-col justify-between w-[52%] px-16 xl:px-20 pb-14">
          <HeroContent />
          <HeroStats />
        </div>


      </div>
    </section>
  );
}
