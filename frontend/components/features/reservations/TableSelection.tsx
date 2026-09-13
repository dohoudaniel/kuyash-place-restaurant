"use client";

import { Home, TreePine, Lock, Check, MapPin, Loader2 } from "lucide-react";
import type { ReservationData } from "@/app/reservations/page";
import type { TableArea } from "@/lib/api/types";

export interface AreaAvailability {
  available: boolean;
  reason?: string;
}

interface TableSelectionProps {
  reservation: ReservationData;
  updateReservation: (data: Partial<ReservationData>) => void;
  areas: TableArea[];
  /** Whether the chosen time is free in each area, keyed by slug. Empty while checking. */
  availability: Record<string, AreaAvailability>;
}

const ICONS: Record<string, typeof Home> = { indoor: Home, outdoor: TreePine, private: Lock };
const COLORS = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b"];

export default function TableSelection({ reservation, updateReservation, areas, availability }: TableSelectionProps) {
  const checking = Object.keys(availability).length === 0;

  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Choose Your Table
      </h2>

      {areas.length === 0 ? (
        <div className="flex items-center gap-2" role="status">
          <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--red)" }} />
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading seating areas…</span>
        </div>
      ) : (
        <div className="grid sm:grid-cols-3 gap-4" role="radiogroup" aria-label="Seating area">
          {areas.map((area, index) => {
            const Icon = ICONS[area.slug] ?? MapPin;
            const color = COLORS[index % COLORS.length];
            const isSelected = reservation.area === area.slug;
            const state = availability[area.slug];
            const unavailable = !checking && !state?.available;
            const features = Array.isArray(area.features) ? (area.features as string[]) : [];

            return (
              <button
                key={area.slug}
                type="button"
                role="radio"
                aria-checked={isSelected}
                disabled={checking || unavailable}
                onClick={() => updateReservation({ area: area.slug })}
                className="relative text-left p-4 rounded-xl border-2 transition-all hover:shadow-lg group disabled:hover:shadow-none disabled:cursor-not-allowed"
                style={{
                  borderColor: isSelected ? color : "var(--gray-mid)",
                  background: isSelected ? `color-mix(in srgb, ${color} 3%, white)` : "white",
                  opacity: unavailable ? 0.5 : 1,
                }}
              >
                {/* Badge */}
                {area.is_premium && !isSelected && (
                  <div className="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: color }}>
                    Premium
                  </div>
                )}

                {/* Selected Checkmark */}
                {isSelected && (
                  <div className="absolute top-3 right-3 w-6 h-6 rounded-full flex items-center justify-center" style={{ background: color }}>
                    <Check className="w-4 h-4 text-white" />
                  </div>
                )}

                {/* Icon */}
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-all group-hover:scale-110"
                  style={{ background: `color-mix(in srgb, ${color} 9%, white)` }}
                >
                  <Icon className="w-6 h-6" style={{ color }} />
                </div>

                {/* Content */}
                <h3 className="font-black text-lg mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                  {area.name}
                </h3>
                <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
                  {area.description}
                </p>

                {/* Features */}
                <ul className="space-y-1">
                  {features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      <div className="w-1 h-1 rounded-full" style={{ background: color }} />
                      {feature}
                    </li>
                  ))}
                </ul>

                {area.surcharge && area.surcharge.amount > 0 && (
                  <p className="text-xs font-bold mt-3" style={{ color: "var(--black)" }}>+{area.surcharge.display} per booking</p>
                )}
                {checking ? (
                  <p className="text-xs font-semibold mt-3" style={{ color: "var(--text-muted)" }}>Checking…</p>
                ) : unavailable ? (
                  <p className="text-xs font-semibold mt-3" style={{ color: "var(--red)" }}>{state?.reason || "Not available at this time"}</p>
                ) : null}
              </button>
            );
          })}
        </div>
      )}

      {/* Additional Info */}
      <div className="mt-4 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
        <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
          <span style={{ color: "var(--red)" }}>Note:</span> Availability is checked live for your time and party size. You&apos;ll see your
          booking reference as soon as you confirm.
        </p>
      </div>
    </div>
  );
}
