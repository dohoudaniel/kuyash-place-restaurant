import { NextResponse, type NextRequest } from "next/server";

/**
 * Two jobs, on every page request.
 *
 * 1. **Content Security Policy.** A fresh nonce per request; Next.js attaches it
 *    to its own scripts, and `'strict-dynamic'` lets those load the rest. Any
 *    script an attacker manages to inject has no nonce and does not run. This is
 *    why the root layout renders per request — a statically built page cannot
 *    carry a per-request nonce.
 *
 * 2. **Protected routes.** Turn away visitors with no session cookie before a
 *    protected page loads. An optimistic check only: it sees whether the cookie
 *    exists, not whether the session is valid. `RequireAuth` confirms it on the
 *    page and the API refuses the data regardless. In production the session
 *    cookie must be scoped to the parent domain (`SESSION_COOKIE_DOMAIN`) or this
 *    proxy never sees it.
 */
const SESSION_COOKIE = "kuyash_session";

const API_ORIGIN = new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").origin;
const WS_ORIGIN = API_ORIGIN.replace(/^http/, "ws");

/**
 * `/orders` is the history list only. `/orders/[id]` stays open: guests track
 * their own order with the token issued at checkout. `/checkout` stays open too.
 * Keep in step with PROTECTED_PATHS in lib/auth/next.ts.
 */
function isProtected(pathname: string): boolean {
  return pathname === "/orders" || pathname === "/account" || pathname.startsWith("/account/");
}

export function contentSecurityPolicy(nonce: string, isDev = process.env.NODE_ENV === "development"): string {
  const directives: Record<string, string[]> = {
    "default-src": ["'self'"],
    // Development needs eval for React's error overlays; production does not.
    "script-src": ["'self'", `'nonce-${nonce}'`, "'strict-dynamic'", ...(isDev ? ["'unsafe-eval'"] : [])],
    // The design system styles with inline `style` attributes throughout, which a
    // nonce cannot cover. Styles cannot run code; scripts are the strict part.
    "style-src": ["'self'", "'unsafe-inline'"],
    // Menu, gallery and team photos (Supabase in production, the API's /media in
    // development) and the hero's photograph.
    "img-src": ["'self'", "blob:", "data:", "https://*.supabase.co", "https://images.unsplash.com", API_ORIGIN],
    "font-src": ["'self'"],
    // The API, live order tracking, and hot reload in development.
    "connect-src": ["'self'", API_ORIGIN, WS_ORIGIN, ...(isDev ? ["ws:"] : [])],
    // The contact page's map.
    "frame-src": ["https://www.google.com"],
    // Social sign-in posts a form to the API, which redirects to the provider.
    // Chrome applies form-action to that redirect too, so the providers' sign-in
    // hosts must be listed or the button silently does nothing.
    "form-action": ["'self'", API_ORIGIN, "https://accounts.google.com", "https://www.facebook.com"],
    "frame-ancestors": ["'none'"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
  };
  const policy = Object.entries(directives).map(([name, values]) => `${name} ${values.join(" ")}`);
  if (!isDev) policy.push("upgrade-insecure-requests");
  return policy.join("; ");
}

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (isProtected(pathname) && !request.cookies.has(SESSION_COOKIE)) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    url.search = "";
    url.searchParams.set("auth", "login");
    url.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(url);
  }

  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const policy = contentSecurityPolicy(nonce);

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", policy);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", policy);
  return response;
}

export const config = {
  matcher: [
    {
      // Every page; not build assets, optimised images or public files.
      source: "/((?!_next/static|_next/image|favicon.ico|images/).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
