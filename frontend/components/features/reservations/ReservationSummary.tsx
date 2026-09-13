"use client";

import { Calendar, Clock, Users, MapPin, Shield, Mail } from "lucide-react";
import type { ReservationData } from "@/app/reservations/page";
import type { Branch, TableArea } from "@/lib/api/types";
import { formatClock } from "@/lib/site/hours";

interface ReservationSummaryProps {
  reservation: ReservationData;
  area?: TableArea;
  branch: Branch | null;
}

export default function ReservationSummary({ reservation, area, branch }: ReservationSummaryProps) {
  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6 lg:sticky lg:top-24" style={{ borderColor: "var(--gray-mid)" }}>
      <h3 className="font-black text-xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Reservation Summary
      </h3>

      <div className="space-y-3 mb-6">
        {/* Date */}
        {reservation.date && (
          <div className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <Calendar className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
            <div>
              <p className="text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>Date</p>
              <p className="font-bold" style={{ color: "var(--black)" }}>
                {new Date(`${reservation.date}T00:00:00`).toLocaleDateString("en-NG", {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            </div>
          </div>
        )}

        {/* Time */}
        {reservation.time && (
          <div className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <Clock className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
            <div>
              <p className="text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>Time</p>
              <p className="font-bold" style={{ color: "var(--black)" }}>{formatClock(reservation.time)}</p>
            </div>
          </div>
        )}

        {/* Guests */}
        {reservation.guests > 0 && (
          <div className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <Users className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
            <div>
              <p className="text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>Guests</p>
              <p className="font-bold" style={{ color: "var(--black)" }}>
                {reservation.guests} {reservation.guests === 1 ? "Person" : "People"}
              </p>
            </div>
          </div>
        )}

        {/* Seating Area */}
        {area && (
          <div className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <MapPin className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
            <div>
              <p className="text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>Seating</p>
              <p className="font-bold" style={{ color: "var(--black)" }}>{area.name}</p>
            </div>
          </div>
        )}

        {/* Contact Info */}
        {reservation.name && (
          <div className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <Users className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
            <div>
              <p className="text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>Contact</p>
              <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{reservation.name}</p>
              {reservation.email && <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{reservation.email}</p>}
              {reservation.phone && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{reservation.phone}</p>}
            </div>
          </div>
        )}

        {/* Special Requests */}
        {reservation.specialRequests && (
          <div className="p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <p className="text-xs font-bold mb-1" style={{ color: "var(--text-muted)" }}>Special Requests</p>
            <p className="text-sm font-semibold" style={{ color: "var(--black)" }}>{reservation.specialRequests}</p>
          </div>
        )}
      </div>

      {/* Restaurant Info */}
      <div className="border-t pt-4" style={{ borderColor: "var(--gray-mid)" }}>
        {branch && (
          <div className="flex items-start gap-3 mb-4">
            <MapPin className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
            <div>
              <p className="font-bold text-sm mb-0.5" style={{ color: "var(--black)" }}>{branch.name}</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {[branch.address_line, branch.city, branch.state].filter(Boolean).join(", ")}
              </p>
              {branch.phone && (
                <a href={`tel:${branch.phone}`} className="text-xs" style={{ color: "var(--text-muted)" }}>{branch.phone}</a>
              )}
            </div>
          </div>
        )}

        {/* Trust Badges */}
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center gap-2 p-2 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <Shield className="w-4 h-4" style={{ color: "#10b981" }} />
            <p className="text-[10px] font-bold" style={{ color: "var(--black)" }}>Live Availability</p>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg" style={{ background: "var(--gray-light)" }}>
            <Mail className="w-4 h-4" style={{ color: "#f59e0b" }} />
            <p className="text-[10px] font-bold" style={{ color: "var(--black)" }}>Email Confirmation</p>
          </div>
        </div>
      </div>
    </div>
  );
}
