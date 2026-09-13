/**
 * Reservation management tokens, per reference.
 *
 * Returned once, when a table is booked, so a guest without an account can
 * cancel from this browser. The confirmation email carries it too.
 */
const STORAGE_KEY = "kuyash-reservations";

function read(): Record<string, string> {
  try {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? (parsed as Record<string, string>) : {};
  } catch {
    return {};
  }
}

export function rememberReservation(reference: string, token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...read(), [reference]: token }));
  } catch {
    /* storage blocked: the confirmation email still carries the link */
  }
}

export function reservationHeaders(reference: string): Record<string, string> | undefined {
  const token = read()[reference];
  return token ? { "X-Reservation-Token": token } : undefined;
}
