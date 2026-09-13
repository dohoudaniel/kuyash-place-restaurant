"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { Heart, LogOut, User } from "lucide-react";
import { IMAGES } from "@/lib/assets/images";
import { useCartStore } from "@/lib/store/cartStore";
import { useWishlistStore } from "@/lib/store/wishlistStore";
import { useAuthStore } from "@/lib/store/authStore";
import { useAuthModalStore } from "@/lib/store/authModalStore";
import NavLinks from "./NavLinks";
import MobileMenu from "./MobileMenu";

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled]     = useState(false);
  const authStatus = useAuthStore((state) => state.status);
  const logout = useAuthStore((state) => state.logout);
  const openAuth = useAuthModalStore((state) => state.open);
  const isSignedIn = authStatus === "authenticated";
  const { getTotalItems } = useCartStore();
  const { getTotalItems: getWishlistCount } = useWishlistStore();
  const cartCount = getTotalItems();
  const wishlistCount = getWishlistCount();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 sm:px-6 md:px-8 lg:px-16 transition-all duration-500"
      style={{
        background: scrolled ? "rgba(10,10,10,0.92)" : "transparent",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        WebkitBackdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid rgba(255,255,255,0.06)" : "none",
        paddingTop: scrolled ? "6px" : "8px",
        paddingBottom: scrolled ? "6px" : "8px",
      }}
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      {/* ── Logo — far left ── */}
      <a href="/" className="shrink-0 relative z-10" style={{ width: "clamp(90px, 20vw, 140px)", height: "clamp(50px, 12vw, 72px)" }}>
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
            width: "clamp(180px, 40vw, 280px)",
            height: "clamp(180px, 40vw, 280px)",
            filter: "drop-shadow(0 4px 12px rgba(217,4,41,0.25))",
          }}
          priority
        />
      </a>

      {/* ── Nav links — true centre ── */}
      <NavLinks />

      {/* ── Right actions ── */}
      <div className="hidden lg:flex items-center gap-3 xl:gap-4 shrink-0">
        <Link
          href="/wishlist"
          className="relative w-9 h-9 xl:w-10 xl:h-10 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105"
          style={{ border: "1.5px solid rgba(255,255,255,0.25)", color: "#fff" }}
          aria-label={`Wishlist (${wishlistCount} items)`}
        >
          <Heart className="w-4 h-4 xl:w-5 xl:h-5" />
          {wishlistCount > 0 && (
            <span
              className="absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
              style={{ background: "var(--red)" }}
            >
              {wishlistCount > 9 ? "9+" : wishlistCount}
            </span>
          )}
        </Link>
        <Link
          href="/cart"
          className="relative w-9 h-9 xl:w-10 xl:h-10 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105"
          style={{ border: "1.5px solid rgba(255,255,255,0.25)", color: "#fff" }}
          aria-label={`Cart (${cartCount} items)`}
        >
          <svg className="w-4 h-4 xl:w-5 xl:h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          {cartCount > 0 && (
            <span
              className="absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
              style={{ background: "var(--red)" }}
            >
              {cartCount > 9 ? "9+" : cartCount}
            </span>
          )}
        </Link>
        {isSignedIn ? (
          <Link
            href="/account"
            className="relative w-9 h-9 xl:w-10 xl:h-10 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105"
            style={{ border: "1.5px solid rgba(255,255,255,0.25)", color: "#fff" }}
            aria-label="My account"
          >
            <User className="w-4 h-4 xl:w-5 xl:h-5" />
          </Link>
        ) : (
          <button
            onClick={() => openAuth("login")}
            className="relative w-9 h-9 xl:w-10 xl:h-10 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105"
            style={{ border: "1.5px solid rgba(255,255,255,0.25)", color: "#fff" }}
            aria-label="Sign in"
          >
            <User className="w-4 h-4 xl:w-5 xl:h-5" />
          </button>
        )}
        {isSignedIn ? (
          <button
            onClick={() => void logout()}
            className="px-4 xl:px-6 py-2 xl:py-2.5 rounded-full text-xs xl:text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95 whitespace-nowrap flex items-center gap-1.5"
            style={{ background: "var(--red)" }}
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        ) : (
          <button
            onClick={() => openAuth("signup")}
            className="px-4 xl:px-6 py-2 xl:py-2.5 rounded-full text-xs xl:text-sm font-bold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95 whitespace-nowrap"
            style={{ background: "var(--red)" }}
          >
            Sign Up
          </button>
        )}
      </div>

      {/* ── Mobile hamburger ── */}
      <button
        className="lg:hidden p-2 z-10"
        style={{ color: "#fff" }}
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle menu"
      >
        <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          {mobileOpen
            ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          }
        </svg>
      </button>

      {/* ── Mobile menu ── */}
      <MobileMenu isOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

    </motion.nav>
  );
}
