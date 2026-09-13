/**
 * Enrolment access tokens, per reference.
 *
 * Returned once to a guest when they enrol (and carried in their emails), so
 * they can pay, check their seat and download their certificate from this
 * browser without an account.
 */
const STORAGE_KEY = "kuyash-enrolments";

function read(): Record<string, string> {
  try {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? (parsed as Record<string, string>) : {};
  } catch {
    return {};
  }
}

export function rememberEnrolment(reference: string, token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...read(), [reference]: token }));
  } catch {
    /* storage blocked: the emailed link still works */
  }
}

export function enrolmentHeaders(reference: string): Record<string, string> | undefined {
  const token = read()[reference];
  return token ? { "X-Enrolment-Token": token } : undefined;
}
