"use client";

import { motion, type Transition } from "framer-motion";
import Navbar from "@/components/layout/Navbar";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 28 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.85, delay, ease: [0.22, 1, 0.36, 1] } satisfies Transition,
});

export default function AcademyHero() {
  return (
    <section
      className="relative min-h-screen w-full overflow-hidden flex flex-col"
      style={{ background: "#fff" }}
    >
      <Navbar />

      {/* ── Centred text content ── */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center px-6 flex-1 min-h-[calc(100vh-80px)]">

        {/* Headline */}
        <motion.h1
          {...fadeUp(0.1)}
          className="leading-[1.05] max-w-4xl mb-5"
          style={{ letterSpacing: "-0.02em" }}
        >
          <span
            className="block font-black"
            style={{
              fontFamily: "var(--font-playfair)",
              fontSize: "clamp(3rem, 6.5vw, 5.5rem)",
              color: "var(--black)",
            }}
          >
            Master the Art of
          </span>
          <span
            className="block font-black"
            style={{
              fontFamily: "var(--font-playfair)",
              fontSize: "clamp(3rem, 6.5vw, 5.5rem)",
              fontStyle: "italic",
              color: "var(--red)",
            }}
          >
            Fine Cuisine.
          </span>
        </motion.h1>

        {/* Subtext */}
        <motion.p
          {...fadeUp(0.2)}
          className="mb-8 max-w-md leading-relaxed"
          style={{
            color: "var(--text-muted)",
            fontSize: "clamp(0.95rem, 1.4vw, 1.05rem)",
          }}
        >
          Train under world-class mentors. Lead kitchens. Define excellence.
        </motion.p>

        {/* CTAs */}
        <motion.div
          {...fadeUp(0.3)}
          className="flex items-center justify-center gap-4 flex-wrap"
        >
          <a
            href="#enroll"
            className="group flex items-center gap-2 px-9 py-4 text-sm font-bold text-white transition-all duration-300 hover:scale-105 active:scale-95"
            style={{
              background: "var(--red)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              boxShadow: "0 8px 28px rgba(217,4,41,0.28)",
            }}
          >
            Enroll Now
            <svg
              className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.5}
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </a>
          <a
            href="#programs"
            className="flex items-center gap-2 px-9 py-4 text-sm font-bold transition-all duration-300 hover:scale-105 active:scale-95"
            style={{
              border: "2px solid var(--black)",
              color: "var(--black)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            Explore Programs
          </a>
        </motion.div>
      </div>

    </section>
  );
}
