"use client";

import { motion } from "framer-motion";

export default function HeroImage() {
  return (
    <>
      {/* Desktop hero image */}
      <div
        className="relative flex-1 self-stretch hidden lg:flex items-center justify-center overflow-hidden lg:max-w-[45%]"
        style={{ minHeight: "100vh", background: "var(--white)" }}
      >
        {/* Soft left-edge fade so panel merges into the left text area */}
        <div
          className="absolute inset-y-0 left-0 z-10 pointer-events-none"
          style={{ width: "12%", background: "linear-gradient(to right, var(--white) 0%, transparent 100%)" }}
        />

        {/* Food image — white/light background dish, fills panel naturally */}
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: "url('https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=1000&q=90')",
            backgroundPosition: "center center",
          }}
        />

        {/* Subtle bottom fade to anchor the image */}
        <div
          className="absolute bottom-0 left-0 right-0 pointer-events-none"
          style={{ height: "20%", background: "linear-gradient(to top, var(--white) 0%, transparent 100%)" }}
        />

        {/* Fast Delivery text — now dark since background is light */}
        <div className="absolute bottom-10 right-10 text-right z-20">
          <div className="w-14 h-px mb-3 ml-auto" style={{ background: "var(--red)" }} />
          <p
            className="font-black leading-tight"
            style={{
              fontFamily: "var(--font-playfair)",
              fontSize: "clamp(1.8rem, 3vw, 2.8rem)",
              fontStyle: "italic",
              color: "var(--black)",
            }}
          >
            Fast<br />Delivery
          </p>
          <div className="w-14 h-px mt-3 ml-auto" style={{ background: "var(--red)" }} />
        </div>

        {/* Floating ingredients */}
        <motion.div className="absolute z-20 text-5xl" style={{ top: "12%", right: "8%" }} animate={{ y: [0, -12, 0] }} transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }} aria-hidden="true">🍅</motion.div>
        <motion.div className="absolute z-20 text-4xl" style={{ top: "6%", right: "36%" }} animate={{ y: [0, -8, 0] }} transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }} aria-hidden="true">🧄</motion.div>
        <motion.div className="absolute z-20 text-4xl" style={{ bottom: "14%", right: "6%" }} animate={{ y: [0, -10, 0] }} transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut", delay: 1 }} aria-hidden="true">🍅</motion.div>
      </div>

      {/* Mobile food image */}
      <div className="lg:hidden w-full relative overflow-hidden" style={{ height: "clamp(240px, 50vw, 320px)", background: "var(--white)" }}>
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "url('https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=900&q=85')" }}
        />
        <div
          className="absolute inset-0 flex items-end justify-end p-4 sm:p-6"
          style={{ background: "linear-gradient(to top, rgba(255,255,255,0.85) 0%, transparent 55%)" }}
        >
          <p
            className="font-black text-xl sm:text-2xl leading-tight"
            style={{ fontFamily: "var(--font-playfair)", fontStyle: "italic", color: "var(--black)" }}
          >
            Fast<br />Delivery
          </p>
        </div>
      </div>
    </>
  );
}
