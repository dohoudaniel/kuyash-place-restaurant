"use client";

import { useEffect, useState } from "react";
import { Trophy, Star, Award, Medal, Crown, Zap } from "lucide-react";
import { loadAwards } from "@/lib/api/site";
import type { Award as AwardData } from "@/lib/api/types";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

const BADGES = [
  { icon: Trophy, color: "#f59e0b" },
  { icon: Star, color: "var(--red)" },
  { icon: Award, color: "#10b981" },
  { icon: Medal, color: "#3b82f6" },
  { icon: Crown, color: "#8b5cf6" },
  { icon: Zap, color: "#ec4899" },
];

/**
 * Awards staff have entered, each with who gave it. The previous section
 * credited the Michelin Guide, TripAdvisor and a "Lagos Food Awards" with
 * honours nothing supports; it now appears only when there is a real award.
 */
export default function AchievementsSection() {
  const { settings } = useSiteInfo();
  const [awards, setAwards] = useState<AwardData[]>([]);

  useEffect(() => {
    let cancelled = false;
    loadAwards().then((data) => !cancelled && setAwards(data)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  if (awards.length === 0) return null;

  const stats = [
    { value: settings?.stat_customers, label: "Happy Guests" },
    { value: settings?.stat_dishes, label: "Dishes" },
    { value: settings?.stat_years, label: "Years Serving" },
    { value: settings?.stat_rating, label: "Avg Rating" },
  ].filter((stat) => stat.value);

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="text-center mb-6">
        <h2 className="font-black text-2xl sm:text-3xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Awards & Recognition
        </h2>
        <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
          Celebrating excellence in culinary arts and service
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {awards.map((award, idx) => {
          const { icon: Icon, color } = BADGES[idx % BADGES.length];
          const content = (
            <>
              <div className="w-14 h-14 rounded-full flex items-center justify-center mb-3" style={{ background: `${color}20` }}>
                <Icon className="w-7 h-7" style={{ color }} />
              </div>
              <h4 className="font-black text-xs sm:text-sm mb-1" style={{ color: "var(--black)" }}>
                {award.title}
              </h4>
              <p className="text-[10px] sm:text-xs" style={{ color: "var(--text-muted)" }}>
                {award.awarded_by}{award.year ? ` · ${award.year}` : ""}
              </p>
            </>
          );
          const className = "flex flex-col items-center text-center p-4 rounded-xl transition-all hover:shadow-lg hover:-translate-y-1";
          const style = { background: `${color}08`, border: `1px solid ${color}30` };
          return award.url ? (
            <a key={`${award.title}-${idx}`} href={award.url} target="_blank" rel="noopener noreferrer" className={className} style={style}>
              {content}
            </a>
          ) : (
            <div key={`${award.title}-${idx}`} className={className} style={style}>
              {content}
            </div>
          );
        })}
      </div>

      {/* Stats */}
      {stats.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-6" style={{ borderTop: "1px solid var(--gray-mid)" }}>
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="font-black text-xl sm:text-2xl mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                {stat.value}
              </p>
              <p className="text-xs font-bold" style={{ color: "var(--text-muted)" }}>
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
