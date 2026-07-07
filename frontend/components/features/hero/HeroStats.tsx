"use client";

import { motion, type Transition } from "framer-motion";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.25, 0.1, 0.25, 1] } satisfies Transition,
});

export default function HeroStats() {
  return (
    <motion.div {...fadeUp(0.7)} className="pb-8 sm:pb-10 lg:pb-16">
      <p className="text-[10px] sm:text-[11px] font-bold uppercase tracking-[0.18em] mb-2" style={{ color: "#fff" }}>
        We are Open From
      </p>
      <p className="text-xs sm:text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>Mon–Sat: 09:00am – 10:00pm</p>
      <p className="text-xs sm:text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>Sunday: 09:00am – 08:00pm</p>

      <div className="flex items-center gap-6 sm:gap-8 mt-5 sm:mt-6">
        <div>
          <p className="text-xl sm:text-2xl font-black" style={{ fontFamily: "var(--font-playfair)", color: "#fff" }}>250+</p>
          <p className="text-[10px] sm:text-xs mt-1" style={{ color: "rgba(255,255,255,0.6)" }}>Food items</p>
        </div>
        <div className="w-px h-6 sm:h-8" style={{ background: "rgba(255,255,255,0.2)" }} />
        <div>
          <p className="text-xl sm:text-2xl font-black" style={{ fontFamily: "var(--font-playfair)", color: "#fff" }}>15k+</p>
          <p className="text-[10px] sm:text-xs mt-1" style={{ color: "rgba(255,255,255,0.6)" }}>Happy customers</p>
        </div>
      </div>
    </motion.div>
  );
}
