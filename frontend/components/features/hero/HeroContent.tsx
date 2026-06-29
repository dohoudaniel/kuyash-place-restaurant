"use client";

import { motion, type Transition } from "framer-motion";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.25, 0.1, 0.25, 1] } satisfies Transition,
});

export default function HeroContent() {
  return (
    <div className="flex flex-col justify-center flex-1 max-w-xl lg:mt-8">
      {/* Tagline pill */}
      <motion.div {...fadeUp(0.1)} className="mb-5 sm:mb-6">
        <span
          className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 rounded-full text-[10px] sm:text-xs font-bold uppercase tracking-widest text-white"
          style={{ background: "var(--red)" }}
        >
          <span>✦</span> Tastefully Classy
        </span>
      </motion.div>

      {/* Headline */}
      <motion.h1 {...fadeUp(0.2)} className="leading-tight mb-4 sm:mb-5" style={{ color: "var(--black)" }}>
        <span className="block font-black" style={{ fontFamily: "var(--font-playfair)", fontSize: "clamp(2rem, 7vw, 4.4rem)", letterSpacing: "-0.02em" }}>
          Experience Dining,
        </span>
        <span className="block font-black" style={{ fontFamily: "var(--font-playfair)", fontSize: "clamp(2rem, 7vw, 4.4rem)", letterSpacing: "-0.02em", fontStyle: "italic", color: "var(--red)" }}>
          Redefined.
        </span>
      </motion.h1>

      {/* Subheadline */}
      <motion.p {...fadeUp(0.3)} className="text-xs sm:text-sm leading-relaxed mb-5 sm:mb-6 max-w-sm" style={{ color: "var(--text-muted)" }}>
        At Kuyash Place, every meal is prepared with passion, premium ingredients,
        and an uncompromising commitment to excellence.
      </motion.p>

      {/* Star rating */}
      <motion.div {...fadeUp(0.4)} className="flex items-center gap-2 mb-6 sm:mb-8 flex-wrap">
        <div className="flex items-center gap-0.5">
          {[...Array(5)].map((_, i) => (
            <svg key={i} className="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 20 20" fill="var(--red)">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          ))}
        </div>
        <span className="text-[10px] sm:text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
          Rated by Thousands of Satisfied Customers
        </span>
      </motion.div>

      {/* CTAs */}
      <motion.div {...fadeUp(0.5)} className="flex items-center gap-3 sm:gap-4 flex-wrap">
        <a
          href="#menu"
          className="flex items-center gap-2 px-6 sm:px-8 py-3 sm:py-3.5 rounded-full text-xs sm:text-sm font-bold text-white transition-all duration-200 hover:scale-105 active:scale-95"
          style={{ background: "var(--red)", boxShadow: "0 8px 28px rgba(217,4,41,0.35)" }}
        >
          <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          Order Now
        </a>
        <a
          href="#menu"
          className="flex items-center gap-2 px-6 sm:px-8 py-3 sm:py-3.5 rounded-full text-xs sm:text-sm font-bold transition-all duration-200 hover:scale-105 active:scale-95"
          style={{ border: "2px solid var(--black)", color: "var(--black)" }}
        >
          View Menu
        </a>
      </motion.div>

      {/* Slide indicators */}
      <motion.div {...fadeUp(0.6)} className="flex items-center gap-2 mt-6 sm:mt-8">
        <span className="w-6 sm:w-8 h-1 rounded-full" style={{ background: "var(--red)" }} />
        <span className="w-3 sm:w-4 h-1 rounded-full" style={{ background: "var(--gray-mid)" }} />
        <span className="w-3 sm:w-4 h-1 rounded-full" style={{ background: "var(--gray-mid)" }} />
      </motion.div>
    </div>
  );
}
