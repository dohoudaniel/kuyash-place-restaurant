"use client";

import { NAV_LINKS } from "@/lib/data/navigation";

export default function FooterNavigation() {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.18em] mb-5" style={{ color: "var(--red)" }}>
        Navigation
      </p>
      <ul className="flex flex-col gap-3">
        {NAV_LINKS.map((link) => (
          <li key={link.label}>
            <a
              href={link.href}
              className="text-sm transition-colors duration-200 hover:text-white"
              style={{ color: "rgba(255,255,255,0.55)" }}
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
