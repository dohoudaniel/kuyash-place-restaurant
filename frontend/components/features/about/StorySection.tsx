"use client";

import { Sparkles } from "lucide-react";

export default function StorySection() {
  return (
    <div className="grid lg:grid-cols-2 gap-6 lg:gap-8">
      {/* Story Content */}
      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: "var(--red)15" }}>
            <Sparkles className="w-6 h-6" style={{ color: "var(--red)" }} />
          </div>
          <h2 className="font-black text-2xl sm:text-3xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Our Story
          </h2>
        </div>

        <div className="space-y-4" style={{ color: "var(--text-muted)" }}>
          <p className="text-sm sm:text-base leading-relaxed">
            Founded in 2015, Kuyash Place began as a dream to create a culinary destination that celebrates the rich flavors
            of Nigerian cuisine while embracing global culinary innovations. What started as a small family-owned restaurant
            has blossomed into one of Lagos's most beloved dining establishments.
          </p>
          <p className="text-sm sm:text-base leading-relaxed">
            Our founder, Chef Emmanuel Kuyash, envisioned a place where traditional recipes passed down through generations
            would meet modern cooking techniques and presentation. This philosophy remains at the heart of everything we do.
          </p>
          <p className="text-sm sm:text-base leading-relaxed">
            Today, we're proud to serve over 500 guests daily, hosting everything from intimate family dinners to grand
            celebrations. Each dish tells a story, and every visit creates memories that last a lifetime.
          </p>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <h3 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Our Journey
        </h3>

        <div className="space-y-4">
          {[
            { year: "2015", title: "The Beginning", desc: "Opened our doors with 10 signature dishes" },
            { year: "2017", title: "First Award", desc: "Best New Restaurant in Lagos" },
            { year: "2019", title: "Expansion", desc: "Added private dining and outdoor patio" },
            { year: "2021", title: "Culinary Excellence", desc: "Michelin Guide recognition" },
            { year: "2023", title: "Digital Innovation", desc: "Launched online ordering platform" },
            { year: "2025", title: "Community Focus", desc: "Started Kuyash Academy for aspiring chefs" },
          ].map((milestone, idx) => (
            <div key={idx} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center font-black text-sm flex-shrink-0"
                  style={{ background: "var(--red)", color: "white" }}
                >
                  {milestone.year.slice(2)}
                </div>
                {idx < 5 && <div className="w-0.5 flex-1 mt-2" style={{ background: "var(--gray-mid)" }} />}
              </div>
              <div className="pb-4">
                <h4 className="font-black text-sm sm:text-base mb-1" style={{ color: "var(--black)" }}>
                  {milestone.title}
                </h4>
                <p className="text-xs sm:text-sm" style={{ color: "var(--text-muted)" }}>
                  {milestone.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
