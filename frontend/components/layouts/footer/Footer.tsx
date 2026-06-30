"use client";

import FooterBrand from "./FooterBrand";
import FooterNavigation from "./FooterNavigation";
import FooterHours from "./FooterHours";
import FooterNewsletter from "./FooterNewsletter";

export default function Footer() {
  return (
    <footer id="contact" style={{ background: "#000000", color: "white" }}>
      <div className="max-w-6xl mx-auto px-8 md:px-16 pt-16 pb-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
          <FooterBrand />
          <FooterNavigation />
          <FooterHours />
          <FooterNewsletter />
        </div>
      </div>

      {/* Bottom bar */}
      <div
        className="max-w-6xl mx-auto px-8 md:px-16 py-5"
        style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }}
      >
        <div className="flex flex-wrap justify-center gap-4 mb-4 text-xs">
          <a href="/privacy" className="hover:text-white transition-colors" style={{ color: "rgba(255,255,255,0.5)" }}>Privacy Policy</a>
          <span style={{ color: "rgba(255,255,255,0.2)" }}>•</span>
          <a href="/terms" className="hover:text-white transition-colors" style={{ color: "rgba(255,255,255,0.5)" }}>Terms of Service</a>
          <span style={{ color: "rgba(255,255,255,0.2)" }}>•</span>
          <a href="/refunds" className="hover:text-white transition-colors" style={{ color: "rgba(255,255,255,0.5)" }}>Refund Policy</a>
          <span style={{ color: "rgba(255,255,255,0.2)" }}>•</span>
          <a href="/cookies" className="hover:text-white transition-colors" style={{ color: "rgba(255,255,255,0.5)" }}>Cookie Policy</a>
          <span style={{ color: "rgba(255,255,255,0.2)" }}>•</span>
          <a href="/accessibility" className="hover:text-white transition-colors" style={{ color: "rgba(255,255,255,0.5)" }}>Accessibility</a>
        </div>
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
          <span>© {new Date().getFullYear()} Kuyash Place Restaurant. All rights reserved.</span>
          <span style={{ color: "var(--red)" }}>Tastefully Classy ✦</span>
        </div>
      </div>
    </footer>
  );
}
