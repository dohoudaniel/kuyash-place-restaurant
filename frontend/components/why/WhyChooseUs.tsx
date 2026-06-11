"use client";

import { motion } from "framer-motion";

const FEATURES = [
  {
    icon: "🌱",
    title: "Farm Fresh Ingredients",
    description: "Directly sourced from Kuyash Integrated Farm — from soil to plate, freshness guaranteed.",
  },
  {
    icon: "👨‍🍳",
    title: "Exceptional Taste",
    description: "Expertly prepared by experienced chefs who treat every dish as a masterpiece.",
  },
  {
    icon: "🚀",
    title: "Fast Delivery",
    description: "Hot, fresh meals delivered to your door in 30 minutes or less.",
  },
  {
    icon: "✨",
    title: "Premium Ambience",
    description: "An unforgettable dining experience that lingers long after the last bite.",
  },
];

export default function WhyChooseUs() {
  return (
    <section id="about" className="py-20 md:py-28 px-8 md:px-16" style={{ background: "var(--off-white)" }}>
      <div className="max-w-6xl mx-auto">

        {/* Heading */}
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] mb-3" style={{ color: "var(--red)" }}>
            Why Kuyash Place
          </span>
          <h2
            className="font-black leading-tight"
            style={{ fontFamily: "var(--font-playfair)", fontSize: "clamp(2rem, 4vw, 3.2rem)", color: "var(--black)" }}
          >
            More Than a Meal —<br />
            <em style={{ color: "var(--red)" }}>An Experience.</em>
          </h2>
        </motion.div>

        {/* Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((feature, i) => (
            <motion.div
              key={feature.title}
              className="bg-white rounded-2xl p-8 flex flex-col gap-4 cursor-default group"
              style={{ border: "1px solid var(--gray-mid)" }}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.55, delay: i * 0.1, ease: [0.25, 0.1, 0.25, 1] }}
              whileHover={{ y: -6, boxShadow: "0 20px 48px rgba(0,0,0,0.10)" }}
            >
              <div
                className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl transition-all duration-300 group-hover:scale-110"
                style={{ background: "rgba(217,4,41,0.08)" }}
              >
                {feature.icon}
              </div>
              <h3 className="font-bold text-base" style={{ color: "var(--black)" }}>
                {feature.title}
              </h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                {feature.description}
              </p>
              <div className="mt-auto">
                <span className="w-8 h-0.5 block rounded-full transition-all duration-300 group-hover:w-14" style={{ background: "var(--red)" }} />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
