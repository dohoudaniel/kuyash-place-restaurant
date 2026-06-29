"use client";

import StatCard from "./StatCard";

const STATS = [
  { value: 250,   suffix: "+",  label: "Food Items"          },
  { value: 15000, suffix: "+",  label: "Happy Customers"     },
  { value: 30,    suffix: " min", label: "Average Delivery"  },
  { value: 100,   suffix: "%",  label: "Fresh Ingredients"   },
];

export default function StatsSection() {
  return (
    <section className="py-16 md:py-20" style={{ background: "var(--black)" }}>
      <div className="max-w-6xl mx-auto px-8 md:px-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-4">
          {STATS.map((stat, i) => (
            <StatCard
              key={stat.label}
              value={stat.value}
              suffix={stat.suffix}
              label={stat.label}
              index={i}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
