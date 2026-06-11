"use client";

import { motion, type Transition } from "framer-motion";
import Navbar from "@/components/layout/Navbar";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.25, 0.1, 0.25, 1] } satisfies Transition,
});

export default function HeroSection() {
  return (
    <section
      className="relative min-h-screen overflow-hidden"
      style={{ background: "var(--white)" }}
    >
      {/* Faint decorative circle watermarks */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute rounded-full" style={{ width: "520px", height: "520px", top: "5%", left: "20%", border: "1.5px solid rgba(217,4,41,0.08)" }} />
        <div className="absolute rounded-full" style={{ width: "360px", height: "360px", top: "18%", left: "30%", border: "1.5px solid rgba(217,4,41,0.05)" }} />
        <div className="absolute rounded-full" style={{ width: "200px", height: "200px", top: "8%", left: "8%", border: "1.5px solid rgba(217,4,41,0.05)" }} />
      </div>

      <Navbar />

      {/* Hero content */}
      <div className="relative z-10 flex flex-col lg:flex-row items-center min-h-screen pt-24">

        {/* ── Left panel ── */}
        <div className="flex-1 flex flex-col justify-between px-8 md:px-16 py-10 lg:py-0 lg:min-h-screen">
          <div className="flex flex-col justify-center flex-1 max-w-xl">

            {/* Tagline pill */}
            <motion.div {...fadeUp(0.1)} className="mb-5">
              <span
                className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest text-white"
                style={{ background: "var(--red)" }}
              >
                <span>✦</span> Tastefully Classy
              </span>
            </motion.div>

            {/* Headline */}
            <motion.h1 {...fadeUp(0.2)} className="leading-tight mb-4" style={{ color: "var(--black)" }}>
              <span className="block font-black" style={{ fontFamily: "var(--font-playfair)", fontSize: "clamp(2.8rem, 5.5vw, 4.4rem)", letterSpacing: "-0.02em" }}>
                Experience Dining,
              </span>
              <span className="block font-black" style={{ fontFamily: "var(--font-playfair)", fontSize: "clamp(2.8rem, 5.5vw, 4.4rem)", letterSpacing: "-0.02em", fontStyle: "italic", color: "var(--red)" }}>
                Redefined.
              </span>
            </motion.h1>

            {/* Subheadline */}
            <motion.p {...fadeUp(0.3)} className="text-sm leading-relaxed mb-6 max-w-sm" style={{ color: "var(--text-muted)" }}>
              At Kuyash Place, every meal is prepared with passion, premium ingredients,
              and an uncompromising commitment to excellence.
            </motion.p>

            {/* Star rating */}
            <motion.div {...fadeUp(0.4)} className="flex items-center gap-2 mb-8">
              <div className="flex items-center gap-0.5">
                {[...Array(5)].map((_, i) => (
                  <svg key={i} className="w-4 h-4" viewBox="0 0 20 20" fill="var(--red)">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <span className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
                Rated by Thousands of Satisfied Customers
              </span>
            </motion.div>

            {/* CTAs */}
            <motion.div {...fadeUp(0.5)} className="flex items-center gap-4 flex-wrap">
              <a
                href="#menu"
                className="flex items-center gap-2 px-8 py-3.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:scale-105 active:scale-95"
                style={{ background: "var(--red)", boxShadow: "0 8px 28px rgba(217,4,41,0.35)" }}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Order Now
              </a>
              <a
                href="#menu"
                className="flex items-center gap-2 px-8 py-3.5 rounded-full text-sm font-bold transition-all duration-200 hover:scale-105 active:scale-95"
                style={{ border: "2px solid var(--black)", color: "var(--black)" }}
              >
                View Menu
              </a>
            </motion.div>

            {/* Slide indicators */}
            <motion.div {...fadeUp(0.6)} className="flex items-center gap-2 mt-8">
              <span className="w-8 h-1 rounded-full" style={{ background: "var(--red)" }} />
              <span className="w-4 h-1 rounded-full" style={{ background: "var(--gray-mid)" }} />
              <span className="w-4 h-1 rounded-full" style={{ background: "var(--gray-mid)" }} />
            </motion.div>
          </div>

          {/* Bottom-left info */}
          <motion.div {...fadeUp(0.7)} className="pb-10 lg:pb-16">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] mb-2" style={{ color: "var(--black)" }}>
              We are Open From
            </p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Mon–Sat: 09:00am – 10:00pm</p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Sunday: 09:00am – 08:00pm</p>

            <div className="flex items-center gap-8 mt-6">
              <div>
                <p className="text-2xl font-black" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>250+</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Food items</p>
              </div>
              <div className="w-px h-8" style={{ background: "var(--gray-mid)" }} />
              <div>
                <p className="text-2xl font-black" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>15k+</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Happy customers</p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* ── Right panel — food on pure white, no dark background ── */}
        <div
          className="relative flex-1 self-stretch hidden lg:flex items-center justify-center overflow-hidden"
          style={{ minHeight: "100vh", background: "var(--white)" }}
        >
          {/* Soft left-edge fade so panel merges into the left text area */}
          <div
            className="absolute inset-y-0 left-0 z-10 pointer-events-none"
            style={{ width: "18%", background: "linear-gradient(to right, var(--white) 0%, transparent 100%)" }}
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
        <div className="lg:hidden w-full relative overflow-hidden" style={{ height: "280px", background: "var(--white)" }}>
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: "url('https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=900&q=85')" }}
          />
          <div
            className="absolute inset-0 flex items-end justify-end p-6"
            style={{ background: "linear-gradient(to top, rgba(255,255,255,0.85) 0%, transparent 55%)" }}
          >
            <p
              className="font-black text-2xl leading-tight"
              style={{ fontFamily: "var(--font-playfair)", fontStyle: "italic", color: "var(--black)" }}
            >
              Fast<br />Delivery
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
