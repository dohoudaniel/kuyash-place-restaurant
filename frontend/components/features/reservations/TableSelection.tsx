"use client";

import { Home, TreePine, Lock, Check } from "lucide-react";
import type { ReservationData } from "@/app/reservations/page";

interface TableSelectionProps {
  reservation: ReservationData;
  updateReservation: (data: Partial<ReservationData>) => void;
}

export default function TableSelection({ reservation, updateReservation }: TableSelectionProps) {
  const tables = [
    {
      type: "indoor" as const,
      icon: Home,
      label: "Indoor Seating",
      description: "Climate-controlled comfort with ambient lighting",
      features: ["Air Conditioned", "Ambient Music", "Cozy Atmosphere"],
      color: "#3b82f6",
    },
    {
      type: "outdoor" as const,
      icon: TreePine,
      label: "Outdoor Patio",
      description: "Fresh air and beautiful garden views",
      features: ["Garden Views", "Natural Light", "Al Fresco Dining"],
      color: "#10b981",
    },
    {
      type: "private" as const,
      icon: Lock,
      label: "Private Room",
      description: "Exclusive space for special occasions",
      features: ["Private Space", "Dedicated Service", "Custom Menu"],
      color: "#8b5cf6",
      badge: "Premium",
    },
  ];

  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Choose Your Table
      </h2>

      <div className="grid sm:grid-cols-3 gap-4">
        {tables.map((table) => {
          const Icon = table.icon;
          const isSelected = reservation.tableType === table.type;

          return (
            <button
              key={table.type}
              onClick={() => updateReservation({ tableType: table.type })}
              className="relative text-left p-4 rounded-xl border-2 transition-all hover:shadow-lg group"
              style={{
                borderColor: isSelected ? table.color : "var(--gray-mid)",
                background: isSelected ? `${table.color}05` : "white",
              }}
            >
              {/* Badge */}
              {table.badge && (
                <div
                  className="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
                  style={{ background: table.color }}
                >
                  {table.badge}
                </div>
              )}

              {/* Selected Checkmark */}
              {isSelected && (
                <div
                  className="absolute top-3 right-3 w-6 h-6 rounded-full flex items-center justify-center"
                  style={{ background: table.color }}
                >
                  <Check className="w-4 h-4 text-white" />
                </div>
              )}

              {/* Icon */}
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-all group-hover:scale-110"
                style={{ background: `${table.color}15` }}
              >
                <Icon className="w-6 h-6" style={{ color: table.color }} />
              </div>

              {/* Content */}
              <h3 className="font-black text-lg mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {table.label}
              </h3>
              <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
                {table.description}
              </p>

              {/* Features */}
              <ul className="space-y-1">
                {table.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                    <div className="w-1 h-1 rounded-full" style={{ background: table.color }} />
                    {feature}
                  </li>
                ))}
              </ul>
            </button>
          );
        })}
      </div>

      {/* Additional Info */}
      <div className="mt-4 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
          <span style={{ color: "var(--red)" }}>Note:</span> Table availability is subject to confirmation. We'll contact you within 1 hour to confirm your reservation.
        </p>
      </div>
    </div>
  );
}
