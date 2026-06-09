import Navbar from "@/components/layout/Navbar";

export default function HeroSection() {
  return (
    <section
      className="relative min-h-screen overflow-hidden"
      style={{ background: "var(--cream)" }}
    >
      {/* Faint decorative circle watermarks */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute rounded-full"
          style={{
            width: "520px",
            height: "520px",
            top: "5%",
            left: "20%",
            border: "1.5px solid rgba(224,91,43,0.10)",
          }}
        />
        <div
          className="absolute rounded-full"
          style={{
            width: "360px",
            height: "360px",
            top: "18%",
            left: "30%",
            border: "1.5px solid rgba(224,91,43,0.07)",
          }}
        />
        <div
          className="absolute rounded-full"
          style={{
            width: "220px",
            height: "220px",
            top: "8%",
            left: "8%",
            border: "1.5px solid rgba(224,91,43,0.06)",
          }}
        />
      </div>

      <Navbar />

      {/* Hero content */}
      <div className="relative z-10 flex flex-col lg:flex-row items-center min-h-[calc(100vh-88px)]">

        {/* ── Left panel ── */}
        <div className="flex-1 flex flex-col justify-between px-6 md:px-14 py-10 lg:py-0 lg:min-h-[calc(100vh-88px)]">

          {/* Main text block */}
          <div className="flex flex-col justify-center flex-1 max-w-xl">
            <h1 className="leading-tight mb-5" style={{ color: "var(--brown-dark)" }}>
              <span
                className="block font-black"
                style={{
                  fontFamily: "var(--font-playfair)",
                  fontSize: "clamp(2.8rem, 5.5vw, 4.2rem)",
                }}
              >
                We bring{" "}
                <em
                  className="not-italic"
                  style={{ color: "var(--orange)", fontStyle: "italic", fontFamily: "var(--font-playfair)" }}
                >
                  the best
                </em>
              </span>
              <span
                className="block font-black"
                style={{
                  fontFamily: "var(--font-playfair)",
                  fontSize: "clamp(2.8rem, 5.5vw, 4.2rem)",
                }}
              >
                <em style={{ color: "var(--orange)", fontStyle: "italic" }}>services</em>{" "}
                ever
              </span>
            </h1>

            <p className="text-sm leading-relaxed mb-8 max-w-sm" style={{ color: "var(--text-muted)" }}>
              Feel confident in every bite — crafted meals you can trust. Delicious
              comfort for daily living, bringing flavor and joy to your table.
            </p>

            {/* CTA row */}
            <div className="flex items-center gap-5">
              <span className="text-2xl font-black" style={{ color: "var(--brown-dark)" }}>
                $7.90
              </span>
              <a
                href="#menu"
                className="flex items-center gap-2 px-7 py-3.5 rounded-full text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 hover:scale-105 active:scale-95"
                style={{ background: "var(--orange)" }}
              >
                {/* Cart icon */}
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Order Now
              </a>
            </div>

            {/* Slide indicators */}
            <div className="flex items-center gap-2 mt-7">
              <span className="w-6 h-1 rounded-full" style={{ background: "var(--orange)" }} />
              <span className="w-4 h-1 rounded-full" style={{ background: "var(--cream-dark)" }} />
              <span className="w-4 h-1 rounded-full" style={{ background: "var(--cream-dark)" }} />
            </div>
          </div>

          {/* Bottom-left info */}
          <div className="pb-10 lg:pb-14">
            <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: "var(--brown-dark)" }}>
              We are Open From
            </p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Mon–Sat: 09:00am–02:00pm</p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Sunday: 09:00am–02:00pm</p>

            {/* Stats */}
            <div className="flex items-center gap-8 mt-6">
              <div>
                <p className="text-2xl font-black" style={{ color: "var(--brown-dark)" }}>250+</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>Food items</p>
              </div>
              <div className="w-px h-8" style={{ background: "var(--cream-dark)" }} />
              <div>
                <p className="text-2xl font-black" style={{ color: "var(--brown-dark)" }}>15k+</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>Happy customers</p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Right panel — food image with diagonal clip ── */}
        <div
          className="relative flex-1 self-stretch hidden lg:flex items-center justify-center overflow-hidden"
          style={{ minHeight: "calc(100vh - 88px)" }}
        >
          {/* Diagonal clip mask */}
          <div
            className="absolute inset-0"
            style={{
              clipPath: "polygon(12% 0%, 100% 0%, 100% 100%, 0% 100%)",
              background: "#1A0E08",
            }}
          >
            {/* Food image fills the clipped area */}
            <div
              className="absolute inset-0 bg-cover bg-center"
              style={{
                backgroundImage: "url('https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=900&q=80')",
                opacity: 0.85,
              }}
            />
            {/* Dark gradient overlay at bottom for "Fast Delivery" text */}
            <div
              className="absolute bottom-0 left-0 right-0"
              style={{
                height: "40%",
                background: "linear-gradient(to top, rgba(10,5,0,0.85) 0%, transparent 100%)",
              }}
            />

            {/* "Fast Delivery" overlay text */}
            <div className="absolute bottom-10 right-10 text-right">
              <div className="w-16 h-0.5 mb-2 ml-auto" style={{ background: "white" }} />
              <p
                className="font-black leading-tight text-white"
                style={{
                  fontFamily: "var(--font-playfair)",
                  fontSize: "clamp(1.8rem, 3.5vw, 3rem)",
                  fontStyle: "italic",
                  textShadow: "0 2px 12px rgba(0,0,0,0.5)",
                }}
              >
                Fast<br />Delivery
              </p>
              <div className="w-16 h-0.5 mt-2 ml-auto" style={{ background: "white" }} />
            </div>
          </div>

          {/* Floating tomato top-right */}
          <div
            className="absolute z-10 text-5xl"
            style={{ top: "12%", right: "8%", filter: "drop-shadow(0 8px 16px rgba(0,0,0,0.25))" }}
            aria-hidden="true"
          >
            🍅
          </div>

          {/* Floating garlic top-center */}
          <div
            className="absolute z-10 text-4xl"
            style={{ top: "6%", right: "36%", filter: "drop-shadow(0 6px 12px rgba(0,0,0,0.2))" }}
            aria-hidden="true"
          >
            🧄
          </div>

          {/* Floating tomato half bottom-right */}
          <div
            className="absolute z-10 text-4xl"
            style={{ bottom: "14%", right: "6%", filter: "drop-shadow(0 6px 12px rgba(0,0,0,0.3))" }}
            aria-hidden="true"
          >
            🍅
          </div>
        </div>

        {/* Mobile food image (full width, below text) */}
        <div
          className="lg:hidden w-full relative overflow-hidden"
          style={{ height: "260px", background: "#1A0E08" }}
        >
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{
              backgroundImage: "url('https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=900&q=80')",
              opacity: 0.82,
            }}
          />
          <div
            className="absolute inset-0 flex items-end justify-end p-6"
            style={{ background: "linear-gradient(to top, rgba(10,5,0,0.7) 0%, transparent 60%)" }}
          >
            <p
              className="font-black text-white text-2xl leading-tight"
              style={{ fontFamily: "var(--font-playfair)", fontStyle: "italic" }}
            >
              Fast<br />Delivery
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
