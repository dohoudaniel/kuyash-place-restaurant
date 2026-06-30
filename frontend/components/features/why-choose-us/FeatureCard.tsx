"use client";

import { motion } from "framer-motion";

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  index: number;
}

export default function FeatureCard({ icon, title, description, index }: FeatureCardProps) {
  return (
    <motion.div
      className="bg-white rounded-2xl p-8 flex flex-col gap-4 cursor-default group"
      style={{ border: "1px solid var(--gray-mid)" }}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.55, delay: index * 0.1, ease: [0.25, 0.1, 0.25, 1] }}
      whileHover={{ y: -6, boxShadow: "0 20px 48px rgba(0,0,0,0.10)" }}
    >
      <div
        className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl transition-all duration-300 group-hover:scale-110"
        style={{ background: "rgba(217,4,41,0.08)" }}
      >
        {icon}
      </div>
      <h3 className="font-bold text-base" style={{ color: "var(--black)" }}>
        {title}
      </h3>
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
        {description}
      </p>
      <div className="mt-auto">
        <span className="w-8 h-0.5 block rounded-full transition-all duration-300 group-hover:w-14" style={{ background: "var(--red)" }} />
      </div>
    </motion.div>
  );
}
