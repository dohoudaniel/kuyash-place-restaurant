"use client";

import { MapPin, Navigation, ExternalLink } from "lucide-react";

export default function MapSection() {
  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8 mb-8" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-black text-xl sm:text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Find Us
        </h3>
        <a
          href="https://maps.google.com"
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
        {/* Map Placeholder */}
        <div className="lg:col-span-2 aspect-video lg:aspect-auto rounded-xl overflow-hidden" style={{ background: "var(--gray-light)", minHeight: "300px" }}>
          <div className="w-full h-full flex flex-col items-center justify-center gap-3">
            <MapPin className="w-16 h-16" style={{ color: "var(--red)" }} />
            <p className="font-bold text-lg" style={{ color: "var(--black)" }}>
              Interactive Map
            </p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              123 Gourmet Street, Victoria Island, Lagos
            </p>
          </div>
        </div>

        {/* Directions Info */}
        <div className="space-y-4">
          <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
            <h4 className="font-black text-sm mb-2" style={{ color: "var(--black)" }}>
              By Car
            </h4>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Ample parking available. Take Ahmadu Bello Way, turn left at Civic Center.
            </p>
          </div>

          <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
            <h4 className="font-black text-sm mb-2" style={{ color: "var(--black)" }}>
              By Public Transport
            </h4>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              BRT stop 2 minutes walk. Falomo roundabout bus stop nearby.
            </p>
          </div>

          <div className="p-4 rounded-xl" style={{ background: "var(--gray-light)" }}>
            <h4 className="font-black text-sm mb-2" style={{ color: "var(--black)" }}>
              Landmarks
            </h4>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Near Eko Hotel & Suites, opposite Federal Palace Hotel.
            </p>
          </div>

          <a
            href="https://maps.google.com"
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
