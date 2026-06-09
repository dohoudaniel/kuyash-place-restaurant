"use client";

import { useState } from "react";
import { NAV_LINKS } from "@/data/navigation";

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="relative z-20 flex items-center justify-between px-6 md:px-12 py-5">
      {/* Logo */}
      <div className="flex items-center">
        <span
          className="text-xl font-black tracking-wide"
          style={{ color: "var(--brown-dark)", fontFamily: "var(--font-inter)" }}
        >
          kuyash<span style={{ color: "var(--orange)" }}>place</span>
        </span>
      </div>

      {/* Desktop nav links */}
      <ul className="hidden md:flex items-center gap-8">
        {NAV_LINKS.map((link) => (
          <li key={link.label}>
            <a
              href={link.href}
              className="text-sm font-medium transition-colors duration-200 hover:text-orange"
              style={{ color: "var(--brown-mid)" }}
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>

      {/* Right side actions */}
      <div className="hidden md:flex items-center gap-3">
        {/* Cart icon */}
        <button
          className="w-10 h-10 rounded-full flex items-center justify-center transition-colors duration-200 hover:bg-cream-dark"
          style={{ border: "1.5px solid #E0D4C8" }}
          aria-label="Cart"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </button>

        {/* Call Now */}
        <a
          href="tel:+15559636"
          className="px-5 py-2.5 rounded-full text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95"
          style={{ background: "var(--orange)" }}
        >
          Call Now
        </a>
      </div>

      {/* Mobile hamburger */}
      <button
        className="md:hidden p-2 rounded-lg transition-colors"
        style={{ color: "var(--brown-dark)" }}
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle menu"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          {mobileOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Mobile menu */}
      {mobileOpen && (
        <div
          className="absolute top-full left-0 right-0 flex flex-col gap-1 px-6 py-4 md:hidden shadow-lg"
          style={{ background: "var(--cream)", borderTop: "1px solid var(--cream-dark)" }}
        >
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="py-2.5 text-base font-medium transition-colors hover:text-orange"
              style={{ color: "var(--brown-mid)", borderBottom: "1px solid var(--cream-dark)" }}
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <a
            href="tel:+15559636"
            className="mt-3 text-center py-3 rounded-full text-sm font-semibold text-white"
            style={{ background: "var(--orange)" }}
          >
            Call Now
          </a>
        </div>
      )}
    </nav>
  );
}
