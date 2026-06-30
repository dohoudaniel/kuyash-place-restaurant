"use client";

import type { ReservationData } from "@/app/reservations/page";

interface GuestInfoFormProps {
  reservation: ReservationData;
  updateReservation: (data: Partial<ReservationData>) => void;
}

export default function GuestInfoForm({ reservation, updateReservation }: GuestInfoFormProps) {
  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Your Information
      </h2>

      <div className="space-y-4">
        {/* Name & Email */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Full Name *
            </label>
            <input
              type="text"
              value={reservation.name}
              onChange={(e) => updateReservation({ name: e.target.value })}
              placeholder="John Doe"
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
              Email Address *
            </label>
            <input
              type="email"
              value={reservation.email}
              onChange={(e) => updateReservation({ email: e.target.value })}
              placeholder="john@example.com"
              className="w-full px-4 py-3 rounded-lg border font-semibold"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        {/* Phone */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Phone Number *
          </label>
          <input
            type="tel"
            value={reservation.phone}
            onChange={(e) => updateReservation({ phone: e.target.value })}
            placeholder="+234 123 456 7890"
            className="w-full px-4 py-3 rounded-lg border font-semibold"
            style={{ borderColor: "var(--gray-mid)" }}
          />
        </div>

        {/* Special Requests */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Special Requests (Optional)
          </label>
          <textarea
            value={reservation.specialRequests}
            onChange={(e) => updateReservation({ specialRequests: e.target.value })}
            placeholder="Dietary restrictions, allergies, special occasions, seating preferences..."
            rows={4}
            className="w-full px-4 py-3 rounded-lg border font-semibold resize-none"
            style={{ borderColor: "var(--gray-mid)" }}
          />
        </div>

        {/* Quick Select Tags */}
        <div>
          <p className="text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Quick Add:</p>
          <div className="flex flex-wrap gap-2">
            {["Birthday Celebration", "Anniversary", "Business Dinner", "Vegetarian Menu", "Wheelchair Access", "High Chair Needed"].map(
              (tag) => (
                <button
                  key={tag}
                  onClick={() => {
                    const current = reservation.specialRequests;
                    const newValue = current ? `${current}, ${tag}` : tag;
                    updateReservation({ specialRequests: newValue });
                  }}
                  className="px-3 py-1.5 rounded-full text-xs font-bold transition-all hover:opacity-80"
                  style={{ background: "var(--gray-light)", color: "var(--black)" }}
                >
                  + {tag}
                </button>
              )
            )}
          </div>
        </div>

        {/* Terms */}
        <div className="p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
            By confirming, you agree to our cancellation policy. Please inform us at least 2 hours in advance for any changes or cancellations.
          </p>
        </div>
      </div>
    </div>
  );
}
