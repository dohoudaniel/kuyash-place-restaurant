"use client";

/**
 * One booking, reached from the link in the confirmation email.
 *
 * That email has always pointed at `/reservations/{reference}?token=…` and this
 * page did not exist, so the link landed on the booking form. It also carries
 * the guest's management token: the API now takes that as a header only (a token
 * in a URL reaches access logs, browser history and `Referer`), so the page
 * stores it, strips it from the address bar, and sends it as a header from then
 * on — the same pattern the academy enrolment page uses.
 */

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, CalendarCheck, Clock, Loader2, MapPin, Users, XCircle } from "lucide-react";
import { formatDate } from "@/components/features/orders/statusStyles";
import { ApiError } from "@/lib/api/client";
import { cancelReservation, fetchReservation } from "@/lib/api/reservations";
import type { Reservation } from "@/lib/api/types";
import { rememberReservation } from "@/lib/reservations/tokens";

const STATUS_TONE: Record<string, string> = {
  pending: "#f59e0b",
  confirmed: "#10b981",
  seated: "#3b82f6",
  completed: "#3b82f6",
  cancelled: "var(--text-muted)",
  no_show: "var(--text-muted)",
};

function ReservationView() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const reference = String(params.reference);

  const [booking, setBooking] = useState<Reservation | null>(null);
  const [loadError, setLoadError] = useState<"not_found" | "network" | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // The emailed link carries the token: keep it, then drop it from the address bar.
  const token = searchParams.get("token");
  useEffect(() => {
    if (!token) return;
    rememberReservation(reference, token);
    router.replace(`/reservations/${reference}`);
  }, [token, reference, router]);

  useEffect(() => {
    if (token) return; // wait for the replace above, so the header is stored first
    let cancelled = false;
    fetchReservation(reference)
      .then((data) => {
        if (cancelled) return;
        setBooking(data);
        setLoadError(null);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err instanceof ApiError && err.status === 404 ? "not_found" : "network");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [reference, token]);

  const cancel = async () => {
    setCancelling(true);
    setActionError(null);
    try {
      setBooking(await cancelReservation(reference));
      setConfirmCancel(false);
    } catch (err) {
      setActionError(
        err instanceof ApiError ? err.message : "We couldn't cancel that booking. Please try again."
      );
    } finally {
      setCancelling(false);
    }
  };

  if (loadError === "not_found") {
    return (
      <div className="bg-white rounded-xl border p-8 max-w-md w-full mx-auto text-center" style={{ borderColor: "var(--gray-mid)" }}>
        <XCircle className="w-12 h-12 mx-auto mb-4" style={{ color: "var(--text-muted)" }} />
        <h1 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          We couldn&apos;t find that booking
        </h1>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          Open the link in your confirmation email — it carries the key to your booking.
        </p>
        <Link
          href="/reservations"
          className="inline-flex w-full items-center justify-center px-6 py-3.5 rounded-full text-sm font-bold text-white transition-all hover:opacity-90"
          style={{ background: "var(--red)" }}
        >
          Book a Table
        </Link>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="flex justify-center py-24">
        {loadError === "network" ? (
          <p role="alert" className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
            We couldn&apos;t load your booking. Please check your connection.
          </p>
        ) : (
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} aria-label="Loading booking" />
        )}
      </div>
    );
  }

  const tone = STATUS_TONE[booking.status] ?? "var(--text-muted)";

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link href="/reservations" className="inline-flex items-center gap-2 text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
        <ArrowLeft className="w-4 h-4" /> Reservations
      </Link>

      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide mb-1" style={{ color: "var(--text-muted)" }}>
              {booking.reference}
            </p>
            <h1 className="font-black text-2xl sm:text-3xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              {booking.guest_name}
            </h1>
          </div>
          <span className="shrink-0 text-xs font-bold px-3 py-1.5 rounded-full text-white" style={{ background: tone }}>
            {booking.status_display}
          </span>
        </div>

        <dl className="grid sm:grid-cols-2 gap-4">
          {[
            { icon: CalendarCheck, label: "When", value: formatDate(booking.reserved_for) },
            { icon: Clock, label: "For", value: `${booking.duration_minutes} minutes` },
            { icon: Users, label: "Party", value: `${booking.party_size} ${booking.party_size === 1 ? "guest" : "guests"}` },
            { icon: MapPin, label: "Where", value: [booking.area?.name, booking.table_number && `Table ${booking.table_number}`].filter(Boolean).join(" · ") || "To be assigned" },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-start gap-3">
              <Icon className="w-5 h-5 mt-0.5 shrink-0" style={{ color: "var(--red)" }} />
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</dt>
                <dd className="text-sm font-semibold" style={{ color: "var(--black)" }}>{value}</dd>
              </div>
            </div>
          ))}
        </dl>

        {booking.special_requests && (
          <p className="mt-6 text-sm rounded-lg px-4 py-3" style={{ background: "var(--off-white)", color: "var(--black)" }}>
            <span className="font-bold">Your note: </span>{booking.special_requests}
          </p>
        )}

        {actionError && (
          <p role="alert" className="mt-6 text-sm font-medium" style={{ color: "var(--red)" }}>{actionError}</p>
        )}

        {booking.can_cancel && (
          <div className="mt-8 pt-6 border-t" style={{ borderColor: "var(--gray-mid)" }}>
            {confirmCancel ? (
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  type="button"
                  onClick={cancel}
                  disabled={cancelling}
                  className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-full font-bold text-sm text-white transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ background: "var(--red)" }}
                >
                  {cancelling && <Loader2 className="w-4 h-4 animate-spin" />}
                  Yes, cancel this booking
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmCancel(false)}
                  disabled={cancelling}
                  className="px-6 py-3 rounded-full font-bold text-sm border transition-all hover:opacity-80 disabled:opacity-50"
                  style={{ borderColor: "var(--gray-mid)", color: "var(--black)" }}
                >
                  Keep it
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmCancel(true)}
                className="px-6 py-3 rounded-full font-bold text-sm border transition-all hover:opacity-80"
                style={{ borderColor: "var(--gray-mid)", color: "var(--black)" }}
              >
                Cancel this booking
              </button>
            )}
            <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
              Need a different time? Cancel and book again, or call us.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ReservationPage() {
  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-16" style={{ background: "var(--off-white)" }}>
      <div className="container-custom">
        <Suspense
          fallback={
            <div className="flex justify-center py-24">
              <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--red)" }} aria-label="Loading booking" />
            </div>
          }
        >
          <ReservationView />
        </Suspense>
      </div>
    </div>
  );
}
