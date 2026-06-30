"use client";

import { motion, AnimatePresence } from "framer-motion";

const NAV_LINKS = [
  { label: "Home",             href: "/",              highlight: false },
  { label: "Menu",             href: "/menu",          highlight: false },
  { label: "Catering",         href: "/catering",      highlight: false },
  { label: "Reservations",     href: "/reservations",  highlight: false },
  { label: "Gallery",          href: "/gallery",       highlight: false },
  { label: "About",            href: "/about",         highlight: false },
  { label: "Contact",          href: "/contact",       highlight: false },
  { label: "Kuyash Academy",   href: "/academy",       highlight: true  },
];

interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function MobileMenu({ isOpen, onClose }: MobileMenuProps) {
  return (
    <AnimatePresence>
      {isOpen && (
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
              onClick={onClose}
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
  );
}
