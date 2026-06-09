import { NAV_LINKS } from "@/data/navigation";

export default function Footer() {
  return (
    <footer
      id="contact"
      className="px-6 md:px-14 py-12"
      style={{ background: "#000000", color: "white" }}
    >
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-10">
        {/* Brand */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div
              className="w-8 h-8 rounded-md flex items-center justify-center text-white text-sm font-black"
              style={{ background: "var(--orange)" }}
            >
              K
            </div>
            <span className="text-xl font-black tracking-wide">
              kuyash<span style={{ color: "var(--orange)" }}>place</span>
            </span>
          </div>
          <p className="text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.55)" }}>
            Crafted meals you can trust. Bringing flavor and joy to your table every single day.
          </p>
        </div>

        {/* Links */}
        <div>
          <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: "var(--orange)" }}>
            Navigation
          </p>
          <ul className="flex flex-col gap-2">
            {NAV_LINKS.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  className="text-sm transition-colors duration-200 hover:text-orange"
                  style={{ color: "rgba(255,255,255,0.6)" }}
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Contact */}
        <div id="contact-info">
          <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: "var(--orange)" }}>
            Contact
          </p>
          <ul className="flex flex-col gap-2 text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>
            <li>+1 555 96 36 36</li>
            <li>hello@kuyashplace.com</li>
            <li>Mon–Sat: 09:00am – 02:00pm</li>
            <li>Sunday: 09:00am – 02:00pm</li>
          </ul>
        </div>
      </div>

      <div
        className="max-w-6xl mx-auto mt-10 pt-6 text-xs text-center"
        style={{ borderTop: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.35)" }}
      >
        © {new Date().getFullYear()} Kuyash Place Restaurant. All rights reserved.
      </div>
    </footer>
  );
}
