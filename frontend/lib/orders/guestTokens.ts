/**
 * Guest order access tokens.
 *
 * A guest has no account, so the backend issues a token when their order is
 * placed — once, in that response only. It is what lets them track the order,
 * pay for it, and download its receipt. Lose it and the order is only reachable
 * through the confirmation email, so it is kept in this browser per reference.
 */
const STORAGE_KEY = "kuyash-guest-orders";

function read(): Record<string, string> {
  try {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? (parsed as Record<string, string>) : {};
  } catch {
    return {};
  }
}

export function rememberGuestOrder(reference: string, token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...read(), [reference]: token }));
  } catch {
    /* storage blocked: the order is still reachable from the confirmation email */
  }
}

export function guestTokenFor(reference: string): string | null {
  return read()[reference] ?? null;
}

/** Headers for a guest's request about one of their orders, if this browser placed it. */
export function guestHeaders(reference: string): Record<string, string> | undefined {
  const token = guestTokenFor(reference);
  return token ? { "X-Guest-Token": token } : undefined;
}
