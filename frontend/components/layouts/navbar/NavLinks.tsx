"use client";

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

export default function NavLinks() {
  return (
    <ul className="hidden lg:flex items-center gap-4 xl:gap-6 2xl:gap-8 absolute left-1/2 -translate-x-1/2">
      {NAV_LINKS.map((link) => (
        <li key={link.label}>
          {link.highlight ? (
            <a
              href={link.href}
              className="text-xs xl:text-sm font-bold tracking-wide px-3 xl:px-4 py-1.5 rounded-full text-white transition-all duration-200 hover:opacity-90 hover:scale-105 whitespace-nowrap"
              style={{ background: "var(--red)", boxShadow: "0 4px 14px rgba(217,4,41,0.35)" }}
            >
              {link.label}
            </a>
          ) : (
            <a
              href={link.href}
              className="text-xs xl:text-sm font-semibold tracking-wide transition-colors duration-200 hover:text-red relative group whitespace-nowrap"
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
  );
}
