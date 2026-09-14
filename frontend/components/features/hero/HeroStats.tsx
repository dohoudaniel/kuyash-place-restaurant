"use client";

import { motion, type Transition } from "framer-motion";
import { summariseHours } from "@/lib/site/hours";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease: [0.25, 0.1, 0.25, 1] } satisfies Transition,
});

/**
 * Opening hours and headline figures from the API. The hardcoded version
 * disagreed with itself about the hours (the data file said 02:00pm, this
 * component 10:00pm) and claimed 250+ dishes.
 */
export default function HeroStats() {
  const { settings, hours } = useSiteInfo();
  const schedule = hours ? summariseHours(hours.hours) : [];
  const stats = [
    { value: settings?.stat_dishes, label: "Dishes" },
    { value: settings?.stat_customers, label: "Happy customers" },
  ].filter((stat) => stat.value);

  return (
    <motion.div {...fadeUp(0.7)} className="pb-8 sm:pb-10 lg:pb-16">
      {schedule.length > 0 && (
        <>
          <p className="text-[10px] sm:text-[11px] font-bold uppercase tracking-[0.18em] mb-2" style={{ color: "#fff" }}>
            We are Open From
          </p>
          {schedule.map((row) => (
            <p key={row.days} className="text-xs sm:text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>{row.days}: {row.time}</p>
          ))}
        </>
      )}

      {stats.length > 0 && (
        <div className="flex items-center gap-6 sm:gap-8 mt-5 sm:mt-6">
          {stats.map((stat, index) => (
            <div key={stat.label} className="flex items-center gap-6 sm:gap-8">
              {index > 0 && <div className="w-px h-6 sm:h-8" style={{ background: "rgba(255,255,255,0.2)" }} />}
              <div>
                <p className="text-xl sm:text-2xl font-black" style={{ fontFamily: "var(--font-playfair)", color: "#fff" }}>{stat.value}</p>
                <p className="text-[10px] sm:text-xs mt-1" style={{ color: "rgba(255,255,255,0.6)" }}>{stat.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
