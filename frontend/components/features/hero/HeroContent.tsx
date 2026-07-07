"use client";

import { motion, type Transition } from "framer-motion";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.65, delay, ease: [0.25, 0.1, 0.25, 1] } satisfies Transition,
});

export default function HeroContent() {
  return (
    <div className="flex flex-col pt-8 lg:pt-12">
      {/* Tagline pill */}
      <motion.div {...fadeUp(0.1)} className="mb-5">
        <span
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-widest text-white"
          style={{ background: "var(--red)" }}
        >
          <span>✦</span> Tastefully Classy
        </span>
      </motion.div>

      {/* Headline — 3 lines: Experience / Dining, / Redefined. */}
      <motion.h1 {...fadeUp(0.2)} className="mb-5" style={{ lineHeight: 1.08 }}>
        <span
          className="block font-black text-white"
          style={{
            fontFamily: "var(--font-playfair)",
            fontSize: "clamp(2.6rem, 4.6vw, 4rem)",
            letterSpacing: "-0.01em",
          }}
        >
          Experience
        </span>
        <span
          className="block font-black text-white"
          style={{
            fontFamily: "var(--font-playfair)",
            fontSize: "clamp(2.6rem, 4.6vw, 4rem)",
            letterSpacing: "-0.01em",
          }}
        >
          Dining,
        </span>
        <span
          className="block font-black"
          style={{
            fontFamily: "var(--font-playfair)",
            fontSize: "clamp(2.6rem, 4.6vw, 4rem)",
            letterSpacing: "-0.01em",
            fontStyle: "italic",
            color: "var(--red)",
          }}
        >
          Redefined.
        </span>
      </motion.h1>

      {/* Subheadline */}
      <motion.p
        {...fadeUp(0.3)}
        className="mb-5 max-w-100"
        style={{
          fontSize: "clamp(0.8rem, 1.1vw, 0.9rem)",
          lineHeight: 1.65,
          color: "rgba(255,255,255,0.55)",
        }}
      >
        At Kuyash Place, every meal is prepared with passion, premium ingredients,
        and an uncompromising commitment to excellence.
      </motion.p>

      {/* Star rating */}
      <motion.div {...fadeUp(0.4)} className="flex items-center gap-2 mb-7">
        <div className="flex items-center gap-0.5">
          {[...Array(5)].map((_, i) => (
            <svg key={i} className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="var(--red)">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          ))}
        </div>
        <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", fontWeight: 600 }}>
          Rated by Thousands of Satisfied Customers
        </span>
      </motion.div>

      {/* CTAs */}
      <motion.div {...fadeUp(0.5)} className="flex items-center gap-3 flex-wrap mb-7">
        <a
          href="/menu"
          className="flex items-center gap-2 rounded-full font-bold text-white transition-all duration-200 hover:scale-105 active:scale-95"
          style={{
            background: "var(--red)",
            boxShadow: "0 6px 24px rgba(217,4,41,0.45)",
            fontSize: "0.82rem",
            padding: "12px 28px",
          }}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          Order Now
        </a>
        <a
          href="/menu"
          className="flex items-center gap-2 rounded-full font-bold transition-all duration-200 hover:scale-105 active:scale-95"
          style={{
            border: "2px solid var(--red)",
            color: "#fff",
            fontSize: "0.82rem",
            padding: "12px 28px",
          }}
        >
          View Menu
        </a>
      </motion.div>

      {/* Slide indicators */}
      <motion.div {...fadeUp(0.6)} className="flex items-center gap-2">
        <span className="w-7 h-0.75 rounded-full" style={{ background: "var(--red)" }} />
        <span className="w-4 h-0.75 rounded-full" style={{ background: "rgba(255,255,255,0.2)" }} />
        <span className="w-4 h-0.75 rounded-full" style={{ background: "rgba(255,255,255,0.2)" }} />
      </motion.div>
    </div>
  );
}
