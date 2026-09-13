import { NextResponse, type NextRequest } from "next/server";

/**
 * Turn away visitors with no session cookie before a protected page loads.
 *
 * An optimistic check only: it sees whether the cookie exists, not whether the
 * session behind it is still valid. `RequireAuth` confirms the session on the
 * page, and the API refuses the data regardless — this just saves a signed-out
 * visitor from watching an account page load and then empty itself.
 *
 * In development the API on :8000 and Next.js on :3000 share the `localhost`
 * cookie jar. In production the session cookie must be scoped to the parent
 * domain (`SESSION_COOKIE_DOMAIN`, enforced by the backend's kuyash.E012 check)
 * or this proxy will never see it.
 */
const SESSION_COOKIE = "kuyash_session";

export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();

  const url = request.nextUrl.clone();
  const next = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  url.pathname = "/";
  url.search = "";
  url.searchParams.set("auth", "login");
  url.searchParams.set("next", next);
  return NextResponse.redirect(url);
}

export const config = {
  // `/orders` is the history list only. `/orders/[id]` stays open: guests track
  // their own order with the token issued at checkout, and the API returns 404
  // for anyone else's. `/checkout` stays open too — guest checkout is supported.
  // Must match PROTECTED_PATHS in lib/auth/next.ts (matchers have to be literals).
  matcher: ["/account/:path*", "/orders"],
};
