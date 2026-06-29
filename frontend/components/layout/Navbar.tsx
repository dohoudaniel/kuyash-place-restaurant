"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { IMAGES } from "@/lib/assets/images";

const NAV_LINKS = [
  { label: "Home",             href: "/",              highlight: false },
  { label: "Menu",             href: "#menu",          highlight: false },
  { label: "Reservations",     href: "#reservations",  highlight: false },
  { label: "Gallery",          href: "#gallery",       highlight: false },
  { label: "About",            href: "#about",         highlight: false },
  { label: "Contact",          href: "#contact",       highlight: false },
  { label: "Kuyash Academy",   href: "#academy",       highlight: true  },
];

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled]     = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 md:px-16 transition-all duration-500"
      style={{
        background: scrolled ? "rgba(255,255,255,0.85)" : "transparent",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        WebkitBackdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid rgba(0,0,0,0.06)" : "none",
        paddingTop: scrolled ? "8px" : "12px",
        paddingBottom: scrolled ? "8px" : "12px",
      }}
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      {/* ── Logo — far left ── */}
      <a href="/" className="shrink-0 relative" style={{ width: "140px", height: "72px" }}>
        <Image
          src={IMAGES.brand.logo}
          alt="Kuyash Place"
          width={280}
          height={280}
          className="object-contain absolute"
          style={{
            top: "50%",
            left: 0,
            transform: "translateY(-50%)",
            width: "280px",
            height: "280px",
            filter: "drop-shadow(0 4px 12px rgba(217,4,41,0.25))",
          }}
          priority
        />
      </a>

      {/* ── Nav links — true centre ── */}
      <ul className="hidden lg:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
        {NAV_LINKS.map((link) => (
          <li key={link.label}>
            {link.highlight ? (
              <a
                href={link.href}
                className="text-[14px] font-bold tracking-wide px-4 py-1.5 rounded-full text-white transition-all duration-200 hover:opacity-90 hover:scale-105"
                style={{ background: "var(--red)", boxShadow: "0 4px 14px rgba(217,4,41,0.35)" }}
              >
                {link.label}
              </a>
            ) : (
              <a
                href={link.href}
                className="text-[14px] font-semibold tracking-wide transition-colors duration-200 hover:text-red relative group"
                style={{ color: "var(--black)" }}
              >
                {link.label}
                <span
                  className="absolute -bottom-1 left-0 w-0 h-0.5 group-hover:w-full transition-all duration-300 rounded-full"
                  style={{ background: "var(--red)" }}
                />
              </a>
            )}
          </li>
        ))}
      </ul>

      {/* ── Right actions ── */}
      <div className="hidden lg:flex items-center gap-4 shrink-0">
        <button
          className="w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200 hover:bg-gray-mid hover:scale-105"
          style={{ border: "1.5px solid var(--gray-mid)" }}
          aria-label="Cart"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </button>
        <a
          href="#menu"
          className="px-6 py-2.5 rounded-full text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95"
          style={{ background: "var(--red)" }}
        >
          Order Online
        </a>
      </div>

      {/* ── Mobile hamburger ── */}
      <button
        className="lg:hidden p-2"
        style={{ color: "var(--black)" }}
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle menu"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          {mobileOpen
            ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          }
        </svg>
      </button>

      {/* ── Mobile menu ── */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="absolute top-full left-0 right-0 flex flex-col gap-1 px-6 py-5 lg:hidden shadow-xl"
            style={{ background: "rgba(255,255,255,0.96)", backdropFilter: "blur(16px)", borderTop: "1px solid var(--gray-mid)" }}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="py-3 text-base font-semibold transition-colors hover:text-red"
                style={{
                  color: link.highlight ? "var(--red)" : "var(--black)",
                  borderBottom: "1px solid var(--gray-mid)",
                  fontWeight: link.highlight ? 800 : 600,
                }}
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <a
              href="#menu"
              className="mt-3 text-center py-3 rounded-full text-sm font-bold text-white"
              style={{ background: "var(--red)" }}
            >
              Order Online
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}
