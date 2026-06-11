"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";

const STATS = [
  { value: 250,   suffix: "+",  label: "Food Items"          },
  { value: 15000, suffix: "+",  label: "Happy Customers"     },
  { value: 30,    suffix: " min", label: "Average Delivery"  },
  { value: 100,   suffix: "%",  label: "Fresh Ingredients"   },
];

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

export default function StatsSection() {
  return (
    <section className="py-16 md:py-20" style={{ background: "var(--black)" }}>
      <div className="max-w-6xl mx-auto px-8 md:px-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-4">
          {STATS.map((stat, i) => (
            <motion.div
              key={stat.label}
              className="flex flex-col items-center text-center"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.6, delay: i * 0.12, ease: [0.25, 0.1, 0.25, 1] }}
            >
              <p
                className="font-black leading-none mb-2"
                style={{ fontFamily: "var(--font-playfair)", fontSize: "clamp(2.4rem, 5vw, 3.6rem)", color: "var(--red)" }}
              >
                <Counter value={stat.value} suffix={stat.suffix} />
              </p>
              <p className="text-sm font-medium tracking-wide" style={{ color: "rgba(255,255,255,0.55)" }}>
                {stat.label}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
