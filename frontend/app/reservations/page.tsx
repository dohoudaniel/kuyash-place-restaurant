"use client";

import { useEffect, useRef, useState } from "react";
import { Calendar, Users, Sparkles, Check, ChevronLeft, ChevronRight, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import ReservationHero from "@/components/features/reservations/ReservationHero";
import TableSelection, { type AreaAvailability } from "@/components/features/reservations/TableSelection";
import GuestInfoForm from "@/components/features/reservations/GuestInfoForm";
import ReservationSummary from "@/components/features/reservations/ReservationSummary";
import { ApiError, newIdempotencyKey } from "@/lib/api/client";
import { bookTable, cancelReservation, fetchAreas, fetchAvailability } from "@/lib/api/reservations";
import type { Reservation, ReservationSlot, TableArea } from "@/lib/api/types";
import { formatClock } from "@/lib/site/hours";
import { useSiteInfo } from "@/lib/site/useSiteInfo";
import { useAuthStore } from "@/lib/store/authStore";

export interface ReservationData {
  date: string;
  /** HH:MM from the availability slots. */
  time: string;
  guests: number;
  /** Table area slug. */
  area: string;
  name: string;
  email: string;
  phone: string;
  specialRequests: string;
}

const EMPTY: ReservationData = { date: "", time: "", guests: 2, area: "", name: "", email: "", phone: "", specialRequests: "" };

function localToday(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

/**
 * Book a table against real availability.
 *
 * The previous wizard offered a fixed list of eighteen times regardless of the
 * date or party size, three hardcoded table types, and ended in
 * `alert("Reservation submitted!")`. Nothing was booked.
 */
export default function ReservationsPage() {
  const user = useAuthStore((state) => state.user);
  const { branch } = useSiteInfo();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [reservation, setReservation] = useState<ReservationData>(EMPTY);
  const [areas, setAreas] = useState<TableArea[]>([]);
  const [slots, setSlots] = useState<ReservationSlot[] | null>(null);
  const [slotsVersion, setSlotsVersion] = useState(0);
  const [availability, setAvailability] = useState<Record<string, AreaAvailability>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booked, setBooked] = useState<Reservation | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const attemptKey = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchAreas().then((list) => !cancelled && setAreas(list)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // Slots for the chosen date and party size, across all areas.
  useEffect(() => {
    if (!reservation.date) return;
    const controller = new AbortController();
    fetchAvailability({ date: reservation.date, partySize: reservation.guests }, { signal: controller.signal })
      .then((result) => setSlots(result.slots))
      .catch(() => {
        if (!controller.signal.aborted) setSlots([]);
      });
    return () => controller.abort();
  }, [reservation.date, reservation.guests, slotsVersion]);

  // On the table step: is the chosen time free in each area?
  useEffect(() => {
    if (step !== 2 || !reservation.date || !reservation.time || areas.length === 0) return;
    let cancelled = false;
    Promise.all(
      areas.map((area) =>
        fetchAvailability({ date: reservation.date, partySize: reservation.guests, area: area.slug })
          .then((result) => {
            const slot = result.slots.find((s) => s.time === reservation.time);
            return [area.slug, { available: Boolean(slot?.available), reason: slot?.reason }] as const;
          })
          .catch(() => [area.slug, { available: false, reason: "Couldn't check this area." }] as const)
      )
    ).then((entries) => {
      if (!cancelled) setAvailability(Object.fromEntries(entries));
    });
    return () => {
      cancelled = true;
    };
  }, [step, reservation.date, reservation.time, reservation.guests, areas]);

  const updateReservation = (data: Partial<ReservationData>) => {
    setReservation((prev) => {
      const next = { ...prev, ...data };
      // A different date or party size can make the chosen time and table unavailable.
      if ((data.date !== undefined && data.date !== prev.date) || (data.guests !== undefined && data.guests !== prev.guests)) {
        next.time = "";
        next.area = "";
      }
      if (data.time !== undefined && data.time !== prev.time) next.area = "";
      return next;
    });
    if (data.date !== undefined || data.guests !== undefined) setSlots(null);
    if (data.time !== undefined || data.date !== undefined || data.guests !== undefined) setAvailability({});
  };

  const goNext = () => {
    setError(null);
    if (step === 2) {
      // Prefill contact details for a signed-in customer, without overwriting anything typed.
      setReservation((prev) => ({
        ...prev,
        name: prev.name || user?.full_name || "",
        email: prev.email || user?.email || "",
        phone: prev.phone || user?.phone || "",
      }));
    }
    setStep((prev) => (prev + 1) as 1 | 2 | 3);
  };

  const confirm = async () => {
    attemptKey.current ??= newIdempotencyKey();
    setSubmitting(true);
    setError(null);
    try {
      const result = await bookTable(
        {
          area: reservation.area,
          date: reservation.date,
          time: reservation.time,
          party_size: reservation.guests,
          guest_name: reservation.name.trim(),
          guest_email: reservation.email.trim(),
          guest_phone: reservation.phone.trim(),
          special_requests: reservation.specialRequests.trim(),
        },
        attemptKey.current
      );
      attemptKey.current = null;
      setBooked(result);
    } catch (err) {
      if (err instanceof ApiError && err.isNetworkError) {
        setError("We couldn't reach the restaurant. Please try again — you won't be booked twice.");
      } else if (err instanceof ApiError && err.code === "slot_unavailable") {
        attemptKey.current = null;
        setError("Sorry — that time was just taken. Please choose another.");
        updateReservation({ time: "" });
        setSlotsVersion((v) => v + 1);
        setStep(1);
      } else {
        attemptKey.current = null;
        const fields = err instanceof ApiError ? Object.values(err.fieldErrors) : [];
        setError(fields[0] ?? (err instanceof ApiError ? err.message : "We couldn't book your table. Please try again."));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const cancelBooking = async () => {
    if (!booked) return;
    setCancelling(true);
    setError(null);
    try {
      setBooked(await cancelReservation(booked.reference));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "We couldn't cancel that booking. Please call us.");
    } finally {
      setCancelling(false);
    }
  };

  const selectedArea = areas.find((area) => area.slug === reservation.area);
  const canProceed = () => {
    if (step === 1) return Boolean(reservation.date && reservation.time && reservation.guests > 0);
    if (step === 2) return Boolean(reservation.area && availability[reservation.area]?.available);
    return Boolean(reservation.name.trim() && reservation.email.trim() && reservation.phone.trim());
  };

  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <ReservationHero />

      <div className="container-custom py-6 sm:py-8">
        {booked ? (
          <div className="max-w-xl mx-auto bg-white rounded-xl border p-8 text-center" style={{ borderColor: "var(--gray-mid)" }}>
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: booked.status === "cancelled" ? "var(--gray-light)" : "#10b98115" }}>
              {booked.status === "cancelled" ? <AlertCircle className="w-8 h-8" style={{ color: "var(--text-muted)" }} /> : <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />}
            </div>
            <h2 className="font-black text-2xl mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              {booked.status === "cancelled" ? "Booking cancelled" : "Your table is booked"}
            </h2>
            <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
              Reference <strong style={{ color: "var(--black)" }}>{booked.reference}</strong> · {booked.status_display}
            </p>
            <dl className="grid grid-cols-2 gap-3 text-left mb-6">
              {[
                ["When", new Date(booked.reserved_for).toLocaleString("en-NG", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })],
                ["Guests", `${booked.party_size} ${booked.party_size === 1 ? "person" : "people"}`],
                ["Where", booked.area.name],
                ["Table", booked.table_number || "Assigned on arrival"],
              ].map(([label, value]) => (
                <div key={label} className="p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
                  <dt className="text-xs font-bold" style={{ color: "var(--text-muted)" }}>{label}</dt>
                  <dd className="font-bold text-sm" style={{ color: "var(--black)" }}>{value}</dd>
                </div>
              ))}
            </dl>
            {booked.status !== "cancelled" && (
              <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
                We&apos;ve emailed the details to {booked.guest_email}.
              </p>
            )}
            {error && <p role="alert" className="text-sm font-semibold mb-4" style={{ color: "var(--red)" }}>{error}</p>}
            <div className="flex gap-3">
              {booked.can_cancel && booked.status !== "cancelled" && (
                <button onClick={cancelBooking} disabled={cancelling} className="flex-1 px-6 py-3 rounded-lg font-bold text-sm disabled:opacity-50" style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}>
                  {cancelling ? "Cancelling..." : "Cancel Booking"}
                </button>
              )}
              <button
                onClick={() => {
                  setBooked(null);
                  setReservation(EMPTY);
                  setSlots(null);
                  setAvailability({});
                  setStep(1);
                }}
                className="flex-1 px-6 py-3 rounded-lg font-bold text-sm text-white"
                style={{ background: "var(--red)" }}
              >
                Book Another Table
              </button>
            </div>
          </div>
        ) : (
          <>
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
                            background: isCompleted || isActive ? "var(--red)" : "var(--gray-light)",
                            color: isCompleted || isActive ? "white" : "var(--text-muted)",
                          }}
                        >
                          {isCompleted ? <Check className="w-5 h-5" /> : <Icon className="w-5 h-5" />}
                        </div>
                        <p className="text-xs sm:text-sm font-bold text-center" style={{ color: isActive || isCompleted ? "var(--black)" : "var(--text-muted)" }}>
                          {s.label}
                        </p>
                      </div>
                      {idx < 2 && <div className="h-0.5 flex-1 mx-2" style={{ background: step > s.num ? "var(--red)" : "var(--gray-mid)" }} />}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Content Grid */}
            <div className="grid lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                {step === 1 && (
                  <DateTimeStep reservation={reservation} updateReservation={updateReservation} slots={slots} />
                )}
                {step === 2 && (
                  <TableSelection reservation={reservation} updateReservation={updateReservation} areas={areas} availability={availability} />
                )}
                {step === 3 && <GuestInfoForm reservation={reservation} updateReservation={updateReservation} />}

                {error && (
                  <p role="alert" className="mt-4 flex items-center gap-2 text-sm font-semibold" style={{ color: "var(--red)" }}>
                    <AlertCircle className="w-4 h-4" />
                    {error}
                  </p>
                )}

                {/* Navigation Buttons */}
                <div className="flex gap-3 mt-6">
                  {step > 1 && (
                    <button
                      onClick={() => setStep((prev) => (prev - 1) as 1 | 2 | 3)}
                      disabled={submitting}
                      className="px-6 py-3 rounded-lg font-bold flex items-center gap-2 transition-all hover:opacity-80"
                      style={{ background: "var(--gray-mid)", color: "var(--black)" }}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Back
                    </button>
                  )}
                  <button
                    onClick={() => (step < 3 ? goNext() : confirm())}
                    disabled={!canProceed() || submitting}
                    className="flex-1 px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all disabled:opacity-40"
                    style={{ background: "var(--red)", color: "white" }}
                  >
                    {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                    {step === 3 ? (submitting ? "Booking..." : "Confirm Reservation") : "Continue"}
                    {step < 3 && <ChevronRight className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="lg:col-span-1">
                <ReservationSummary reservation={reservation} area={selectedArea} branch={branch} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function DateTimeStep({
  reservation,
  updateReservation,
  slots,
}: {
  reservation: ReservationData;
  updateReservation: (data: Partial<ReservationData>) => void;
  slots: ReservationSlot[] | null;
}) {
  const guestOptions = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20];

  return (
    <div className="bg-white rounded-xl border p-4 sm:p-6" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Select Date & Time
      </h2>

      <div className="space-y-4">
        {/* Date */}
        <div>
          <label htmlFor="reservation-date" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Date
          </label>
          <input
            id="reservation-date"
            type="date"
            value={reservation.date}
            onChange={(e) => updateReservation({ date: e.target.value })}
            min={localToday()}
            className="w-full px-4 py-3 rounded-lg border font-semibold"
            style={{ borderColor: "var(--gray-mid)" }}
          />
        </div>

        {/* Number of Guests */}
        <fieldset>
          <legend className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Number of Guests
          </legend>
          <div className="grid grid-cols-6 gap-2">
            {guestOptions.map((num) => (
              <button
                key={num}
                type="button"
                role="radio"
                aria-checked={reservation.guests === num}
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
        </fieldset>

        {/* Time Slots */}
        <fieldset>
          <legend className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
            Available Time Slots
          </legend>
          {!reservation.date ? (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Choose a date to see available times.</p>
          ) : slots === null ? (
            <div className="flex items-center gap-2" role="status">
              <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--red)" }} />
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Checking availability…</span>
            </div>
          ) : slots.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>We&apos;re not taking reservations on this date. Please try another day.</p>
          ) : !slots.some((slot) => slot.available) ? (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Fully booked for {reservation.guests} on this date. Please try another day or a smaller party.</p>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-64 overflow-y-auto">
              {slots.map((slot) => {
                const isSelected = reservation.time === slot.time;
                return (
                  <button
                    key={slot.time}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    disabled={!slot.available}
                    title={slot.available ? undefined : slot.reason}
                    onClick={() => updateReservation({ time: slot.time })}
                    className="px-3 py-2 rounded-lg font-bold text-xs sm:text-sm transition-all disabled:opacity-40 disabled:line-through disabled:cursor-not-allowed"
                    style={{
                      background: isSelected ? "var(--red)" : "white",
                      color: isSelected ? "white" : "var(--black)",
                      border: isSelected ? "2px solid var(--red)" : "1px solid var(--gray-mid)",
                    }}
                  >
                    {formatClock(slot.time)}
                  </button>
                );
              })}
            </div>
          )}
        </fieldset>
      </div>
    </div>
  );
}
