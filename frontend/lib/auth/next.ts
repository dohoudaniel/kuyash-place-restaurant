/**
 * Where to send someone after they sign in.
 *
 * Only same-site relative paths are accepted. `?next=https://evil.example` or
 * `?next=//evil.example` would otherwise turn the sign-in flow into an open
 * redirect that lends this site's name to a phishing page.
 */
export function safeNext(value: string | null | undefined, fallback = "/"): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return fallback;
  }
  return value;
}

/** Routes that need a signed-in customer. Kept in one place for proxy and pages. */
export const PROTECTED_PATHS = ["/account", "/orders"] as const;
