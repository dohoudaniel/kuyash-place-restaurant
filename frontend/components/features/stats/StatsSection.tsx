"use client";

import StatCard from "./StatCard";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

/** "15,000+" → 15000 and "+"; "4.8/5" is not a whole number, so it is shown as written. */
function parseStat(text: string): { value: number | null; suffix: string } {
  const match = text.trim().match(/^(\d[\d,]*)(\D.*)?$/);
  return match ? { value: Number(match[1].replace(/,/g, "")), suffix: match[2] ?? "" } : { value: null, suffix: text };
}

/**
 * Headline figures from site settings, each shown only once the restaurant has
 * entered it. "250+ food items", "15,000+ customers", "30 min delivery" and
 * "100% fresh" were hardcoded — the menu has 18 dishes.
 */
export default function StatsSection() {
  const { settings } = useSiteInfo();
  const stats = [
    { text: settings?.stat_dishes, label: "Dishes" },
    { text: settings?.stat_customers, label: "Happy Customers" },
    { text: settings?.stat_years, label: "Years Serving" },
    { text: settings?.stat_rating, label: "Average Rating" },
  ].filter((stat): stat is { text: string; label: string } => Boolean(stat.text));

  if (stats.length === 0) return null;

  return (
    <section className="py-16 md:py-20" style={{ background: "var(--black)" }}>
      <div className="max-w-6xl mx-auto px-8 md:px-16">
        <div className={`grid grid-cols-2 gap-8 md:gap-4 ${stats.length >= 4 ? "md:grid-cols-4" : stats.length === 3 ? "md:grid-cols-3" : ""}`}>
          {stats.map((stat, i) => {
            const { value, suffix } = parseStat(stat.text);
            return <StatCard key={stat.label} value={value} suffix={suffix} label={stat.label} index={i} />;
          })}
        </div>
      </div>
    </section>
  );
}
