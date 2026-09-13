"use client";

import { MapPin, Navigation, ExternalLink, Clock, Phone } from "lucide-react";
import { summariseHours } from "@/lib/site/hours";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

/**
 * Where to find the restaurant. The directions that used to be here —
 * "BRT stop 2 minutes walk", "opposite Federal Palace Hotel" — were never
 * verified, so the map link is built from the branch's own address and
 * coordinates instead.
 */
export default function MapSection() {
  const { branch, hours } = useSiteInfo();
  if (!branch?.address_line) return null;

  const address = [branch.address_line, branch.city, branch.state].filter(Boolean).join(", ");
  const query = branch.latitude && branch.longitude ? `${branch.latitude},${branch.longitude}` : address;
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
  const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(query)}`;
  const embedUrl = `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`;
  const schedule = hours ? summariseHours(hours.hours) : [];

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8 mb-8" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-black text-xl sm:text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Find Us
        </h3>
        <a
          href={directionsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-all hover:opacity-80"
          style={{ background: "var(--red)", color: "white" }}
        >
          <Navigation className="w-4 h-4" />
          Get Directions
        </a>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 aspect-video lg:aspect-auto rounded-xl overflow-hidden" style={{ background: "var(--gray-light)", minHeight: "300px" }}>
          <iframe
            title={`Map showing ${branch.name}`}
            src={embedUrl}
            className="w-full h-full min-h-[300px] border-0"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        </div>

        <div className="space-y-4">
          <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
            <h4 className="font-black text-sm mb-2 flex items-center gap-2" style={{ color: "var(--black)" }}>
              <MapPin className="w-4 h-4" style={{ color: "var(--red)" }} />
              Address
            </h4>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{address}</p>
          </div>

          {schedule.length > 0 && (
            <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
              <h4 className="font-black text-sm mb-2 flex items-center gap-2" style={{ color: "var(--black)" }}>
                <Clock className="w-4 h-4" style={{ color: "var(--red)" }} />
                Opening Hours
              </h4>
              {schedule.map((row) => (
                <p key={row.days} className="text-xs" style={{ color: "var(--text-muted)" }}>
                  <span className="font-bold" style={{ color: "var(--black)" }}>{row.days}</span> {row.time}
                </p>
              ))}
            </div>
          )}

          {branch.phone && (
            <a href={`tel:${branch.phone}`} className="block p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
              <h4 className="font-black text-sm mb-2 flex items-center gap-2" style={{ color: "var(--black)" }}>
                <Phone className="w-4 h-4" style={{ color: "var(--red)" }} />
                Call Ahead
              </h4>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>Lost? Call us on {branch.phone}.</p>
            </a>
          )}

          <a
            href={mapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-4 rounded-xl text-center font-bold text-sm transition-all hover:shadow-md"
            style={{ background: "#3b82f615", color: "#3b82f6", border: "1px solid #3b82f630" }}
          >
            <ExternalLink className="w-4 h-4 inline mr-2" />
            Open in Google Maps
          </a>
        </div>
      </div>
    </div>
  );
}
