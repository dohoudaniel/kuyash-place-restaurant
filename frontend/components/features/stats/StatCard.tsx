"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";

interface StatCardProps {
  value: number;
  suffix: string;
  label: string;
  index: number;
}

function Counter({ value, suffix }: { value: number; suffix: string }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  useEffect(() => {
    if (!inView) return;
    const duration = 1800;
    const steps = 60;
    const inc = value / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += inc;
      if (current >= value) {
        setDisplay(value);
        clearInterval(timer);
      } else {
        setDisplay(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [inView, value]);

  return (
    <span ref={ref}>
      {display.toLocaleString()}{suffix}
    </span>
  );
}

export default function StatCard({ value, suffix, label, index }: StatCardProps) {
  return (
    <motion.div
      className="flex flex-col items-center text-center"
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6, delay: index * 0.12, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <p
        className="font-black leading-none mb-2"
        style={{ fontFamily: "var(--font-playfair)", fontSize: "clamp(2.4rem, 5vw, 3.6rem)", color: "var(--red)" }}
      >
        <Counter value={value} suffix={suffix} />
      </p>
      <p className="text-sm font-medium tracking-wide" style={{ color: "rgba(255,255,255,0.55)" }}>
        {label}
      </p>
    </motion.div>
  );
}
