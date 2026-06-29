"use client";

import { ChefHat, Users, Award, Sparkles } from "lucide-react";

export default function TeamSection() {
  const team = [
    {
      name: "Chef Emmanuel Kuyash",
      role: "Founder & Head Chef",
      bio: "30+ years of culinary excellence, trained in Paris and Lagos",
      icon: ChefHat,
      color: "var(--red)",
    },
    {
      name: "Sarah Okonkwo",
      role: "Executive Chef",
      bio: "Specializes in fusion cuisine and modern Nigerian dishes",
      icon: Award,
      color: "#f59e0b",
    },
    {
      name: "David Adeleke",
      role: "Pastry Chef",
      bio: "Award-winning dessert creator with international experience",
      icon: Sparkles,
      color: "#8b5cf6",
    },
    {
      name: "Grace Nnamdi",
      role: "Restaurant Manager",
      bio: "15 years in hospitality, ensuring exceptional guest experiences",
      icon: Users,
      color: "#10b981",
    },
  ];

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
          const Icon = member.icon;
          return (
            <div
              key={idx}
              className="bg-white rounded-xl border overflow-hidden transition-all hover:shadow-lg hover:-translate-y-1"
              style={{ borderColor: "var(--gray-mid)" }}
            >
              {/* Avatar Placeholder */}
              <div
                className="h-48 flex items-center justify-center"
                style={{ background: `${member.color}15` }}
              >
                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center"
                  style={{ background: member.color }}
                >
                  <Icon className="w-10 h-10 text-white" />
                </div>
              </div>

              {/* Info */}
              <div className="p-4">
                <h3 className="font-black text-base sm:text-lg mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                  {member.name}
                </h3>
                <p className="text-xs font-bold mb-2" style={{ color: member.color }}>
                  {member.role}
                </p>
                <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {member.bio}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
