/**
 * The one way this app talks to the backend.
 *
 * No component calls `fetch` directly. Everything that makes a request goes
 * through `api()`, so session cookies, CSRF, the anonymous cart token and error
 * handling are done once, here, and nowhere else.
 */

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "");

/** `https://api.kuyashplace.com` — used to resolve relative media paths in development. */
export const API_ORIGIN = new URL(API_URL).origin;

const CSRF_COOKIE = "kuyash_csrftoken";
const CART_TOKEN_KEY = "kuyash-cart-token";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

const isBrowser = typeof window !== "undefined";

/** An RFC 7807 problem document, as every backend error is shaped. */
export interface ProblemDocument {
  type?: string;
  title?: string;
  status?: number;
  /** Stable and machine-readable. Branch on this, never on `detail`. */
  code: string;
  detail?: string;
  /** Present on `validation_error`: field name → messages. */
  errors?: Record<string, unknown>;
  retry_after?: number;
  [extra: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly problem: ProblemDocument;

  constructor(status: number, problem: ProblemDocument) {
    super(problem.detail || problem.title || `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.code = problem.code;
    this.problem = problem;
  }

  /** The request never reached the server. */
  get isNetworkError(): boolean {
    return this.status === 0;
  }

  /** Field-level messages for a `validation_error`, flattened to strings. */
  get fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const [field, value] of Object.entries(this.problem.errors ?? {})) {
      const first = Array.isArray(value) ? value[0] : value;
      if (typeof first === "string") out[field] = first;
    }
    return out;
  }
}

function readCookie(name: string): string {
  if (!isBrowser) return "";
  const row = document.cookie.split("; ").find((entry) => entry.startsWith(`${name}=`));
  return row ? decodeURIComponent(row.slice(name.length + 1)) : "";
}

// localStorage can throw (private windows, blocked storage). A missing cart
// token only means a fresh anonymous cart, so failures are swallowed.
function storageGet(key: string): string | null {
  try {
    return isBrowser ? window.localStorage.getItem(key) : null;
  } catch {
    return null;
  }
}

function storageSet(key: string, value: string): void {
  try {
    if (isBrowser) window.localStorage.setItem(key, value);
  } catch {
    /* see storageGet */
  }
}

/** Whether this browser already has an anonymous cart. */
export function hasCartToken(): boolean {
  return Boolean(storageGet(CART_TOKEN_KEY));
}

export function clearCartToken(): void {
  try {
    if (isBrowser) window.localStorage.removeItem(CART_TOKEN_KEY);
  } catch {
    /* see storageGet */
  }
}

/** The CSRF token, for the rare request that cannot go through `api()` (a form post). */
export function readCsrfToken(): string {
  return readCookie(CSRF_COOKIE);
}

let csrfRequest: Promise<void> | null = null;

/**
 * Make sure the CSRF cookie exists before the first unsafe request.
 *
 * Django only sets it on a response that asks for it, and a visitor whose first
 * action is "add to cart" has not received one yet. Concurrent callers share
 * one request.
 */
export function ensureCsrfCookie(): Promise<void> {
  if (!isBrowser || readCookie(CSRF_COOKIE)) return Promise.resolve();
  csrfRequest ??= fetch(`${API_URL}/auth/csrf/`, { credentials: "include" })
    .then(() => undefined)
    .catch(() => undefined)
    .finally(() => {
      csrfRequest = null;
    });
  return csrfRequest;
}

export interface ApiRequestInit extends Omit<RequestInit, "body"> {
  /** Serialised as JSON. */
  body?: unknown;
  /** Required by the backend on order creation; see `newIdempotencyKey`. */
  idempotencyKey?: string;
}

/**
 * Call the API. `path` is relative to `/api/v1`, e.g. `api("/auth/session/")`.
 *
 * Throws `ApiError` for any non-2xx response and for network failure (status 0).
 */
export async function api<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { body, idempotencyKey, headers: extraHeaders, ...rest } = init;
  const method = (rest.method ?? "GET").toUpperCase();

  const headers = new Headers(extraHeaders);
  headers.set("Accept", "application/json");
  if (body !== undefined) headers.set("Content-Type", "application/json");

  if (!SAFE_METHODS.has(method)) {
    await ensureCsrfCookie();
    const token = readCookie(CSRF_COOKIE);
    if (token) headers.set("X-CSRFToken", token);
  }
  if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);

  const cartToken = storageGet(CART_TOKEN_KEY);
  if (cartToken) headers.set("X-Cart-Token", cartToken);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...rest,
      method,
      headers,
      // Non-negotiable: without it the session cookie is never sent.
      credentials: "include",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, {
      code: "network_error",
      title: "Could not reach Kuyash Place",
      detail: "Check your connection and try again.",
    });
  }

  const echoedCartToken = response.headers.get("X-Cart-Token");
  if (echoedCartToken) storageSet(CART_TOKEN_KEY, echoedCartToken);

  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const problem =
      payload && typeof payload === "object" && "code" in payload
        ? (payload as ProblemDocument)
        : { code: "unknown_error", title: response.statusText, status: response.status };
    throw new ApiError(response.status, problem);
  }
  return payload as T;
}

/**
 * Fetch a binary resource — a PDF receipt — with the same credentials as `api()`.
 * Errors still arrive as problem documents and are thrown as `ApiError`.
 */
export async function apiBlob(path: string, init: { headers?: HeadersInit; signal?: AbortSignal } = {}): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { headers: init.headers, signal: init.signal, credentials: "include" });
  } catch {
    throw new ApiError(0, {
      code: "network_error",
      title: "Could not reach Kuyash Place",
      detail: "Check your connection and try again.",
    });
  }
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      payload && typeof payload === "object" && "code" in payload
        ? (payload as ProblemDocument)
        : { code: "unknown_error", title: response.statusText, status: response.status }
    );
  }
  return response.blob();
}

/** Turn an absolute `next` link from a paginated response into a path for `api()`. */
export function pathFromApiUrl(url: string): string {
  const parsed = new URL(url);
  return `${parsed.pathname.replace(/^\/api\/v1/, "")}${parsed.search}`;
}

/** A fresh key per *attempt* to place an order — reused only when retrying that attempt. */
export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
