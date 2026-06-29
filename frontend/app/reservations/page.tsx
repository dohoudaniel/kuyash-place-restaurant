"use client";

import { useState } from "react";
import { Calendar, Users, Clock, Sparkles, Check, ChevronLeft, ChevronRight } from "lucide-react";
import ReservationHero from "@/components/features/reservations/ReservationHero";
import TableSelection from "@/components/features/reservations/TableSelection";
import GuestInfoForm from "@/components/features/reservations/GuestInfoForm";
import ReservationSummary from "@/components/features/reservations/ReservationSummary";

export interface ReservationData {
  date: string;
  time: string;
  guests: number;
  tableType: "indoor" | "outdoor" | "private" | "";
  name: string;
  email: string;
  phone: string;
  specialRequests: string;
}

export default function ReservationsPage() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [reservation, setReservation] = useState<ReservationData>({
    date: "",
    time: "",
    guests: 2,
    tableType: "",
    name: "",
    email: "",
    phone: "",
    specialRequests: "",
  });

  const updateReservation = (data: Partial<ReservationData>) => {
    setReservation((prev) => ({ ...prev, ...data }));
  };

  const canProceed = () => {
    if (step === 1) return reservation.date && reservation.time && reservation.guests > 0;
    if (step === 2) return reservation.tableType !== "";
    if (step === 3) return reservation.name && reservation.email && reservation.phone;
    return false;
  };

  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <ReservationHero />

      <div className="container-custom py-6 sm:py-8">
        {/* Progress Steps */}
        <div className="bg-white rounded-xl border p-4 mb-6" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex items-center justify-between max-w-2xl mx-auto">
            {[
              { num: 1, label: "Date & Time", icon: Calendar },
              { num: 2, label: "Table", icon: Sparkles },
              { num: 3, label: "Your Info", icon: Users },
            ].map((s, idx) => {
              const Icon = s.icon;
              const isActive = step === s.num;
              const isCompleted = step > s.num;
              return (
                <div key={s.num} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div
                      className="w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center mb-1 sm:mb-2 transition-all"
                      style={{
                        background: isCompleted ? "var(--red)" : isActive ? "var(--red)" : "var(--gray-light)",
                        color: isCompleted || isActive ? "white" : "var(--text-muted)",
                      }}
                    >
                      {isCompleted ? <Check className="w-5 h-5" /> : <Icon className="w-5 h-5" />}
                    </div>
                    <p
                      className="text-xs sm:text-sm font-bold text-center"
                      style={{ color: isActive || isCompleted ? "var(--black)" : "var(--text-muted)" }}
                    >
                      {s.label}
                    </p>
                  </div>
                  {idx < 2 && (
                    <div
                      className="h-0.5 flex-1 mx-2"
                      style={{
                        background: step > s.num ? "var(--red)" : "var(--gray-mid)",
                      }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            {step === 1 && <DateTimeStep reservation={reservation} updateReservation={updateReservation} />}
            {step === 2 && <TableSelection reservation={reservation} updateReservation={updateReservation} />}
            {step === 3 && <GuestInfoForm reservation={reservation} updateReservation={updateReservation} />}

            {/* Navigation Buttons */}
            <div className="flex gap-3 mt-6">
              {step > 1 && (
                <button
                  onClick={() => setStep((prev) => (prev - 1) as 1 | 2 | 3)}
                  className="px-6 py-3 rounded-lg font-bold flex items-center gap-2 transition-all hover:opacity-80"
                  style={{ background: "var(--gray-mid)", color: "var(--black)" }}
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </button>
              )}
              <button
                onClick={() => {
                  if (step < 3) setStep((prev) => (prev + 1) as 1 | 2 | 3);
                  else alert("Reservation submitted!");
                }}
                disabled={!canProceed()}
                className="flex-1 px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all disabled:opacity-40"
                style={{ background: "var(--red)", color: "white" }}
              >
                {step === 3 ? "Confirm Reservation" : "Continue"}
                {step < 3 && <ChevronRight className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="lg:col-span-1">
            <ReservationSummary reservation={reservation} />
          </div>
        </div>
      </div>
    </div>
  );
}

function DateTimeStep({
  reservation,
  updateReservation,
}: {
  reservation: ReservationData;
  updateReservation: (data: Partial<ReservationData>) => void;
}) {
  const timeSlots = [
    "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM", "1:00 PM", "1:30 PM",
    "2:00 PM", "5:00 PM", "5:30 PM", "6:00 PM", "6:30 PM", "7:00 PM",
    "7:30 PM", "8:00 PM", "8:30 PM", "9:00 PM", "9:30 PM", "10:00 PM",
  ];

  const guestOptions = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20];

  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Select Date & Time
      </h2>

      <div className="space-y-4">
        {/* Date */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Date
          </label>
          <input
            type="date"
            value={reservation.date}
            onChange={(e) => updateReservation({ date: e.target.value })}
            min={new Date().toISOString().split("T")[0]}
            className="w-full px-4 py-3 rounded-lg border font-semibold"
            style={{ borderColor: "var(--gray-mid)" }}
          />
        </div>

        {/* Number of Guests */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Number of Guests
          </label>
          <div className="grid grid-cols-6 gap-2">
            {guestOptions.map((num) => (
              <button
                key={num}
                onClick={() => updateReservation({ guests: num })}
                className="px-3 py-2 rounded-lg font-bold text-sm transition-all"
                style={{
                  background: reservation.guests === num ? "var(--red)" : "var(--gray-light)",
                  color: reservation.guests === num ? "white" : "var(--black)",
                  border: reservation.guests === num ? "2px solid var(--red)" : "1px solid var(--gray-mid)",
                }}
              >
                {num}
              </button>
            ))}
          </div>
        </div>

        {/* Time Slots */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Available Time Slots
          </label>
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-64 overflow-y-auto">
            {timeSlots.map((time) => (
              <button
                key={time}
                onClick={() => updateReservation({ time })}
                className="px-3 py-2 rounded-lg font-bold text-xs sm:text-sm transition-all"
                style={{
                  background: reservation.time === time ? "var(--red)" : "white",
                  color: reservation.time === time ? "white" : "var(--black)",
                  border: reservation.time === time ? "2px solid var(--red)" : "1px solid var(--gray-mid)",
                }}
              >
                {time}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
