"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { ChefHat, Users, Award, Sparkles } from "lucide-react";
import { mediaUrl } from "@/lib/api/media";
import { loadTeam } from "@/lib/api/site";
import type { TeamMember } from "@/lib/api/types";

const PLACEHOLDERS = [
  { icon: ChefHat, color: "var(--red)" },
  { icon: Award, color: "#f59e0b" },
  { icon: Sparkles, color: "#8b5cf6" },
  { icon: Users, color: "#10b981" },
];

/**
 * The team, as published in the admin. The four hardcoded profiles carried
 * unconfirmed biographies; the section now appears once staff publish someone.
 */
export default function TeamSection() {
  const [team, setTeam] = useState<TeamMember[]>([]);

  useEffect(() => {
    let cancelled = false;
    loadTeam().then((data) => !cancelled && setTeam(data)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  if (team.length === 0) return null;

  return (
    <div>
      <div className="text-center mb-6">
        <h2 className="font-black text-2xl sm:text-3xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Meet Our Team
        </h2>
        <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
          The talented people behind your unforgettable dining experience
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {team.map((member, idx) => {
          const { icon: Icon, color } = PLACEHOLDERS[idx % PLACEHOLDERS.length];
          const photo = mediaUrl(member.photo_url);
          return (
            <div
              key={`${member.name}-${idx}`}
              className="bg-white rounded-xl border overflow-hidden transition-all hover:shadow-lg hover:-translate-y-1"
              style={{ borderColor: "var(--gray-mid)" }}
            >
              {/* Photo, or the placeholder avatar */}
              <div className="relative h-48 flex items-center justify-center" style={{ background: `${color}15` }}>
                {photo ? (
                  <Image src={photo} alt={member.name} fill sizes="(max-width: 640px) 100vw, 25vw" className="object-cover" />
                ) : (
                  <div className="w-20 h-20 rounded-full flex items-center justify-center" style={{ background: color }}>
                    <Icon className="w-10 h-10 text-white" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="p-4">
                <h3 className="font-black text-base sm:text-lg mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                  {member.name}
                </h3>
                <p className="text-xs font-bold mb-2" style={{ color }}>
                  {member.role}
                </p>
                {member.bio && (
                  <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    {member.bio}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
