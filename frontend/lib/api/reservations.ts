import { reservationHeaders, rememberReservation } from "@/lib/reservations/tokens";
import { api } from "./client";
import type { Reservation, ReservationAvailability, TableArea } from "./types";

export const fetchAreas = () => api<TableArea[]>("/reservations/areas/");

export function fetchAvailability(
  query: { date: string; partySize: number; area?: string },
  init: { signal?: AbortSignal } = {}
) {
  const params = new URLSearchParams({ date: query.date, party_size: String(query.partySize) });
  if (query.area) params.set("area", query.area);
  return api<ReservationAvailability>(`/reservations/availability/?${params}`, init);
}

export interface BookingInput {
  area: string;
  date: string;
  /** HH:MM, as the availability slots give it. */
  time: string;
  party_size: number;
  guest_name: string;
  guest_email: string;
  guest_phone: string;
  special_requests: string;
}

export async function bookTable(input: BookingInput, idempotencyKey: string): Promise<Reservation> {
  const booking = await api<Reservation & { confirmation_token?: string }>("/reservations/", {
    method: "POST",
    body: input,
    idempotencyKey,
  });
  if (booking.confirmation_token) rememberReservation(booking.reference, booking.confirmation_token);
  return booking;
}

export const cancelReservation = (reference: string, reason = "") =>
  api<Reservation>(`/reservations/${encodeURIComponent(reference)}/cancel/`, {
    method: "POST",
    body: { reason },
    headers: reservationHeaders(reference),
  });
