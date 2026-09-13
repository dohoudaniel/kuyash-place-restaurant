# Frontend Integration Guide

File-by-file changes required in `frontend/` to connect to the Django backend.

Read [`FRONTEND_AUDIT.md`](FRONTEND_AUDIT.md) first — it explains *why* each of these is necessary.

---

## 1. New infrastructure to add

### 1.1 `lib/api/client.ts` — the typed API client

Everything goes through one client. No component ever calls `fetch` directly.

```ts
const BASE = process.env.NEXT_PUBLIC_API_URL!;   // https://api.kuyashplace.com/api/v1

class ApiError extends Error {
  constructor(public status: number, public code: string,
              public detail: string, public payload: unknown) { super(detail); }
}

function getCookie(name: string): string {
  return document.cookie.split("; ").find(r => r.startsWith(name + "="))?.split("=")[1] ?? "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRFToken", getCookie("kuyash_csrftoken"));
  }
  const cartToken = localStorage.getItem("kuyash-cart-token");
  if (cartToken) headers.set("X-Cart-Token", cartToken);

  const res = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "include" });

  const echoed = res.headers.get("X-Cart-Token");
  if (echoed) localStorage.setItem("kuyash-cart-token", echoed);

  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, body.code ?? "unknown", body.detail ?? res.statusText, body);
  return body as T;
}
```

`credentials: "include"` is non-negotiable — without it the session cookie is never sent.

### 1.2 `lib/api/types.ts` — generated, not handwritten

```bash
npm run api:sync   # backend schema → lib/api/openapi.yml → lib/api/schema.d.ts
```

`schema.d.ts` is generated and never edited by hand; `lib/api/types.ts` gives the
types readable names. The schema step runs with `--validate --fail-on-warn`, so a
view whose response the generator cannot describe fails the sync instead of
silently disappearing from the types. Wire this into CI so drift between frontend
and backend fails the build rather than production.

### 1.3 `lib/api/money.ts`

```ts
export interface Money { amount: number; currency: string; display: string; }
```

**That is the entire module.** There is no `formatCurrency`, no `parsePrice`, no arithmetic. If you find yourself wanting one, the backend is missing a field.

### 1.4 `lib/store/authStore.ts` — new

```ts
interface AuthStore {
  user: User | null;
  status: "loading" | "authenticated" | "anonymous";
  bootstrap: () => Promise<void>;          // GET /auth/session/
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}
```

Call `bootstrap()` once from a provider in `app/layout.tsx`. **This is the concept that does not currently exist anywhere in the codebase.**

### 1.5 Environment variables

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=https://api.kuyashplace.com/api/v1
```

No payment provider key is needed: checkout redirects to the `authorization_url`
the backend issues. `frontend/.env.example` is committed; `.env.local` is not.

The frontend currently uses **zero** environment variables; nothing is configurable per environment.

### 1.6 `next.config.ts` — currently empty, will break images

```ts
const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "<project-ref>.supabase.co", pathname: "/storage/v1/object/public/**" },
    ],
  },
};
```

Without this, every menu and gallery image from Supabase Storage fails to render.

---

## 2. Files to DELETE

| Path | Why |
|---|---|
| `lib/data/menu.ts` | Menu comes from `GET /catalog/items/` |
| `lib/data/hero.ts` | From `GET /core/settings/` |
| `lib/data/navigation.ts` | Keep only if purely static routing |
| `lib/assets/images.ts` | Image URLs come from the API |
| `lib/store/promoStore.ts` | **Security fix** — promo rules must never ship to the browser |
| `components/layout/` | Dead — superseded by `layouts/` |
| `components/menu/` | Dead — superseded by `features/menu/` |
| `components/hero/` | Dead |
| `components/stats/` | Dead |
| `components/why/` | Dead |
| `components/academy/` | Dead |
| `components/features/menu/MenuItemDetailModal.old.tsx` | Dead |
| Card fields in `checkout/PaymentStep*.tsx` | **PCI-DSS. Delete, do not connect.** |
| Card fields in `checkout/ReviewStep*.tsx` | **PCI-DSS.** These read `cardNumber.slice(-4)` — found by the CI gate, missed by the manual audit. |

Roughly 1,500 lines removed before a single integration line is written.

---

## 3. Files to REWRITE

### 3.1 Auth — `components/features/auth/`

`LoginForm.tsx` — replace the fake:

```tsx
// ❌ current
setTimeout(() => { setIsLoading(false); alert("Login successful!"); onSuccess(); }, 1000);

// ✅ replacement
try {
  await login(formData.email, formData.password);
  onSuccess();
} catch (e) {
  if (e instanceof ApiError && e.code === "email_not_verified") setNeedsVerification(true);
  else setError(e.detail);
}
```

Also: `SignupForm.tsx` same treatment, plus replace the `<div onClick>` checkboxes with real `<input type="checkbox">` (currently keyboard-inaccessible); `ForgotPasswordForm.tsx` call the real endpoint and keep the existing success UI, which is good; `AuthModal.tsx` replace with `components/ui/dialog.tsx` (already installed) for focus trap, Escape and `role="dialog"`.

**New routes:** `app/verify-email/page.tsx`, `app/reset-password/page.tsx`.

### 3.2 Menu — `components/features/menu/`

- `MenuSection.tsx` / `MenuGrid.tsx` — fetch from `/catalog/items/`
- `MenuItem.tsx` — **delete** `parseFloat(item.price.replace(...))`; render `item.price.display`. Use `item.slug` as the ID, never `imageKey`. Render `item.average_rating`, not a hardcoded `5.0`.
- `MenuItemDetailModal.tsx` — **delete** `MOCK_CUSTOMIZATIONS`; render `item.modifier_groups` from the API, enforcing real `min_select`/`max_select`, and show modifier price deltas
- `app/menu/page.tsx` — push search, filter and sort to the server; delete the `return 0` sort stubs and the dietary-filter comment

### 3.3 Cart — `components/features/cart/`

The most important change in the whole integration.

```tsx
// ❌ delete all of this from CartSummary.tsx AND CartSummaryCompact.tsx
const discount = calculateDiscount(subtotal);
const deliveryFee = appliedPromo?.type === "freeDelivery" ? 0 : subtotal > 0 ? 5.00 : 0;
const tax = (subtotal - discount) * 0.075;
const total = subtotal - discount + deliveryFee + tax;

// ✅ replace with
const { totals, vat_note, delivery_note, changes, unavailable, can_checkout, blockers } = cart;
```

Also: render `changes[]` ("the price of X went up") and `unavailable[]` ("X sold out") — states the current UI cannot even detect. Disable checkout when `can_checkout === false`, showing `blockers`. **Delete the `$25+` string** at `CartSummaryCompact.tsx:52`. Collapse `CartSummary`/`CartSummaryCompact` into one component.

### 3.4 Checkout — `app/checkout/page.tsx`

```tsx
// ❌ current
const handleConfirmOrder = () => {
  const orderId = `KYS-${Date.now().toString(36).toUpperCase()}`;
  clearCart();
  router.push(`/orders/${orderId}`);
};

// ✅ replacement
const handleConfirmOrder = async () => {
  setSubmitting(true);
  try {
    const order = await api<Order>("/orders/", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },   // generated once per checkout session
      body: JSON.stringify({
        fulfilment_type: fulfilmentType,
        delivery_address: addressId,
        payment_method: paymentMethod,
        payment_provider: "paystack",
        tip: tipKobo,
        customer_note: note,
        expected_total: cart.totals.grand_total.amount,   // price-changed guard
      }),
    });
    if (order.payment?.authorization_url) {
      window.location.href = order.payment.authorization_url;   // hosted checkout
    } else {
      router.push(`/orders/${order.reference}`);                // cash / transfer
    }
  } catch (e) {
    if (e.code === "price_changed")     showRepricedDialog(e.payload);
    else if (e.code === "item_unavailable") showUnavailableDialog(e.payload);
    else if (e.code === "branch_closed")    showClosedDialog();
    else setError(e.detail);
  } finally { setSubmitting(false); }
};
```

Note what is **absent**: `clearCart()`. The server clears the cart when payment is verified.

Also fix the blank-page bug:

```tsx
{currentStep === 2 && paymentData === null && <PaymentStep … />}   // ❌ blank on Back
{currentStep === 2 && <PaymentStep initialData={paymentData} … />} // ✅
```

**New route:** `app/checkout/complete/page.tsx` — reads `?reference=`, calls `GET /payments/verify/{ref}/`, then redirects to the order page.

### 3.5 Orders

`app/orders/[id]/page.tsx` — delete `getOrderData()` entirely; fetch `GET /orders/{reference}/` and poll every 15s with `If-None-Match` while the order is active. The existing `OrderStatus.tsx` timeline component maps almost 1:1 onto the `timeline[]` array.

`app/orders/page.tsx` — read `GET /orders/` instead of the never-written `orderHistoryStore`; route Reorder through `POST /orders/{ref}/reorder/` and surface the `changes[]` and `unavailable[]` the response carries (same shape as the cart's, so one component renders both).

Two behaviours to build for rather than around:

- The endpoint answers `409 cart_not_empty` when the basket already has lines. Show the customer what reordering would replace and retry with `{"replace": true}` if they agree — do not send `replace` unconditionally.
- A reorder can come back partial, or empty. `added` and `message` say which; do not send the customer to checkout without showing `changes[]` first, since the whole point is that the prices may have moved.

"Download receipt" is `GET /orders/{ref}/receipt/`, which returns `application/pdf` and `409 order_not_paid` for an order that has not been paid for.

**Delete `lib/store/orderHistoryStore.ts`.**

### 3.6 Account — `components/features/account/`

Every section is hardcoded. `ProfileSection` → `GET/PATCH /accounts/me/` (delete "John Doe"); `AddressesSection` → `/accounts/addresses/` CRUD with zone display; `PaymentMethodsSection` → `GET /payments/methods/` (delete Visa •4242); `OrderHistorySection` → `GET /orders/`; `PreferencesSection` → `/accounts/preferences/`. Gate the whole route on auth.

### 3.7 Reservations — `app/reservations/page.tsx`

Replace the 18 hardcoded slots with `GET /reservations/availability/?date=&party_size=&area=`, disabling unavailable slots with their reason. Replace `alert("Reservation submitted!")` with `POST /reservations/` + `Idempotency-Key`, then show the returned reference and confirmation-email notice.

### 3.8 Catering / contact / reviews / academy / rewards / gallery

| File | Replace |
|---|---|
| `app/catering/page.tsx:89` | `alert(...)` + `console.log` → `POST /catering/enquiries/` |
| `components/features/contact/ContactForm.tsx:17` | local state → `POST /support/contact/` |
| `components/features/reviews/ReviewModal.tsx:50` | `alert(...)` → `POST /reviews/` |
| `app/academy/page.tsx:28` | inline `COURSES` array → `GET /academy/courses/` |
| `components/features/academy/EnrollmentModal.tsx:24` | `alert(...)` → `POST /academy/enrolments/` with cohort selection. **Remove the "installment" option** unless a payment-plan model is built (ACA-6) |
| `app/rewards/page.tsx:22` | `useState(false)` → `GET /loyalty/account/` |
| `app/gallery/page.tsx:20` | 20 items with broken image keys → `GET /gallery/` |
| `components/features/chat/*` | local echo → `/support/chat/…` |

---

## 4. Cross-cutting frontend changes

### 4.1 Hydration guard on persisted stores

`zustand` `persist` stores are read during render with no guard, which will produce hydration mismatches once server rendering matters:

```tsx
const [hydrated, setHydrated] = useState(false);
useEffect(() => setHydrated(true), []);
if (!hydrated) return <CartSkeleton />;
```

### 4.2 Route-segment states

There is currently **no** `loading.tsx`, `error.tsx` or `not-found.tsx` anywhere in `app/`. Add them per segment; every API call can now fail.

### 4.3 Auth gating

Gated in step 3: **`/account` and `/orders`** (the history list). `proxy.ts` (Next 16's
renamed middleware) redirects visitors with no `kuyash_session` cookie to
`/?auth=login&next=…`; `RequireAuth` then confirms the session itself, because a
cookie can outlive the session behind it. Neither is the security boundary — the API
refuses the data regardless.

Deliberately **not** gated, correcting the earlier version of this section:

- `/checkout` — guest checkout is a supported flow (`place_order(guest=…)`); gating it
  would remove a feature the backend was built for.
- `/orders/[id]` — guests track their order with the `guest_token` issued at
  checkout, and the API returns 404 to anyone else.
- `/wishlist` — guests keep a browser wishlist; signing in merges it into the account
  (step 10). Gating it would take a working feature away from guests.

For the proxy to see the session cookie in production it must be scoped to the shared
parent domain (`SESSION_COOKIE_DOMAIN`; the backend's `kuyash.E012` check enforces it).

### 4.4 Server Components

`/terms`, `/privacy`, `/cookies`, `/accessibility`, `/refunds`, `/help` and `/about` are marked `"use client"` for no reason. Convert to Server Components fetching from `GET /core/legal/{slug}/` — **live as of Phase 2.6**, along with `GET /core/legal/` for the footer link list.

Delete the hardcoded copy in those route files rather than keeping it as a fallback. The point of serving them from the backend is that the published wording and what the cart charges are checked against each other at deploy (`kuyash.E002`); a stale copy in the bundle is outside that check and reintroduces exactly the contradiction it exists to prevent.

Render `body` as markdown, and show `version` / `effective_from` — customers are entitled to know when the terms they are being held to last changed.

---

## 5. Integration order

Follow this sequence; each step is independently shippable.

1. ✅ API client, generated types, `authStore`, env vars, `next.config.ts` images
2. ✅ **Delete** the dead trees and the card fields (before writing integration code, not after)
3. ✅ Auth: login, signup, reset, verify, session bootstrap, route gating
4. ✅ Catalogue: menu list, detail, real modifiers, server-side filtering
5. ✅ Cart: server cart, server totals, promo application
6. ✅ Checkout + payments: order creation, hosted checkout, completion page
7. ✅ Orders: tracking with polling, history
8. ✅ Account: profile, addresses
9. — **Phase 1 ships here** —
10. ✅ Reservations, catering, contact, wishlist sync
11. Academy, rewards, reviews, gallery, chat

---

### 5.1 Steps 1–2 delivered

**Built on the existing design system, not beside it.** No change to
`app/globals.css`, `components/ui/`, the brand tokens or the fonts. Rewritten
screens keep their original markup, classes and `var(--…)` colours; only what they
do changed.

Added:

- `lib/api/client.ts` — `api()`, `ApiError` (branch on `.code`; `.fieldErrors` for
  validation), lazy CSRF priming before the first unsafe request, cart-token echo,
  network failure as status `0`. `credentials: "include"` on every call.
- `lib/api/schema.d.ts` (generated), `lib/api/types.ts` (aliases),
  `lib/api/money.ts` (`Money` aliased from the schema), `lib/api/media.ts`
  (resolves `/media/…` against the API origin in development).
- `lib/store/authStore.ts` — **not persisted**; the session cookie is the truth.
  `bootstrap()` runs once from `components/providers/AuthProvider.tsx` in the root
  layout. `register()` does not sign in, because email verification is mandatory.
- `next.config.ts` — Supabase public-object `remotePatterns`, the API's `/media/`
  in development, and `dangerouslyAllowLocalIP` **in development only** (Next 16
  otherwise refuses to optimise images from `localhost`).

Deleted — 20 files, 2,878 lines: the six legacy trees, `MenuItemDetailModal.old`,
and every duplicate nothing imported (`CheckoutSidebar`, `CheckoutProgressCompact`,
`DeliveryStepCompact`, `PaymentStepCompact`, `ReviewStepCompact`, `CartItem`,
`CartSummary`). Note the checkout route used the **non**-Compact steps; the Compact
ones were dead.

Card fields: `PaymentStep` keeps its three-option selector and loses every input —
"Pay Online" explains the hosted page. `ReviewStep` no longer prints a fragment of
a typed card number. `PaymentMethodsSection` reads `GET /payments/methods/` with
loading, empty, error and per-card busy states; forget and set-default are real.
`KNOWN_FRONTEND_DEBT` is empty and the gate passes.

**Deliberately not deleted yet:** `lib/store/promoStore.ts`, `lib/data/menu.ts`
and `lib/assets/images.ts` from the §2 table. Live screens still import them, and
deleting them before their replacements land (steps 4 and 5) would break the
build rather than remove debt. They go in the step that replaces them.

Backend contract fixes this pass forced — each would have surfaced as a broken or
untyped screen:

- Five views had no describable response and were **omitted** from the schema
  (reorder, forget-card, today's book, overdue enquiries, open tickets).
- Cart/order `totals`, payment `amount`s and the KDS `grand_total` were untyped
  dictionaries; now `Totals` / `Money`.
- `status` enums had hash-suffixed names (`Status889Enum`) that would churn.
- `save_card` was never declared, so saved-card consent was unreachable.
- Supabase image URLs pointed at the private S3 endpoint (DEPLOYMENT.md §5.1).

Verified: `tsc` clean; `next build` passes; ESLint 48 → 40 errors and 13 → 12
warnings with **no new findings** (the remainder is pre-existing, mostly unescaped
apostrophes in legal copy that step 4.4 replaces); backend 872 passed.

---

### 5.2 Step 3 delivered

Sign-in is real. Same design as before — the forms keep their markup, classes and
colours; the dialog keeps its look but is now built on the `Dialog` primitives, so it
traps focus, closes on Escape and is announced as a dialog.

- `LoginForm` — real sign-in; `email_not_verified` offers to resend the link in place.
- `SignupForm` — real registration with field-level errors; the password minimum is
  now 10, matching the backend (the form said 8, which the API rejected); the terms and
  marketing checkboxes are real `<input type="checkbox">`s instead of clickable `<div>`s.
- `ForgotPasswordForm` — real request; the copy no longer confirms whether an account
  exists.
- New routes `/verify-email` (signs the customer in), `/reset-password` (uid + token
  from the emailed link) and `/auth/callback` (social sign-in return, with a message
  for each allauth error code).
- `authModalStore` lets any screen ask for sign-in; `AuthProvider` mounts the dialog
  once and opens it from `?auth=login&next=…`. `next` is restricted to same-site paths.
- Google/Facebook buttons appear only for providers the backend has credentials for
  (read from `/_allauth/browser/v1/config`), and start a real form post to allauth.
- Gating: `proxy.ts` + `RequireAuth` on `/account` and `/orders` (see §4.3).
- `next` upgraded 16.2.6 → **16.3.5**, clearing two critical RCE advisories.

**Running the client against a live server found seven backend defects that no unit
test or type check had caught.** All fixed and covered by tests:

| # | Defect | Effect |
|---|---|---|
| 1 | CORS preflight did not allow `X-Cart-Token`, `X-Guest-Token`, `Idempotency-Key` | The browser would block every request once a cart existed, and every order placement |
| 2 | Sign-in endpoints were CSRF-exempt (DRF exempts unauthenticated views) and accept form posts | Login CSRF: a foreign page could sign a visitor into an attacker's account |
| 3 | Password reset deleted the requester's own session mid-request | A signed-in reset changed the password, then showed an HTML 400 |
| 4 | `allauth.urls` not mounted | Every social sign-in raised `NoReverseMatch` — it could never have worked |
| 5 | `HEADLESS_FRONTEND_URLS["socialaccount_login_error"]` missing | Every social failure, including a customer pressing Cancel at Google, was a 500 |
| 6 | Takeover backstop answered with JSON on the provider callback | A refused Facebook sign-in stranded the customer on a raw JSON page on the API domain |
| 7 | OpenAPI schema claimed login/verify returned a bare user; they return `{user}` | The generated client read the wrong shape |

Also: providers with blank credentials are no longer registered, so the config endpoint
never offers a button that leads to an error; broad `except Exception` handlers in the
password views were narrowed to validation errors.

Verified: backend 898 passed; `tsc` clean; `next build` passes; ESLint 40 → 36 errors,
12 warnings, no new findings; a scripted cross-origin run of register → unverified
login → verify → session → signed-in reset → reused link → new-password login →
social failure → logout passes end to end with zero server errors.

Not yet done, and not part of step 3: `ProfileSection` and `PreferencesSection` still
`alert()` on save (step 8, Account).

---

### 5.3 Steps 4–7 delivered

The whole purchase path now runs on the API: browse → configure → cart → checkout →
pay → track → reorder. Built on the existing design system; the screens keep their
markup, classes and colours.

**Why four steps landed together.** Every "Add to cart" button fed the local cart with
`parseFloat`-ed naira strings, and the cart summary did its own discount, delivery and
VAT arithmetic. Menu items from the API carry integer-kobo `Money`, so wiring the menu
alone meant either client-side money arithmetic (forbidden) or two carts that
disagreed. Once the cart lived on the server, a "Confirm" that wrote to the local order
history would have recorded kobo as naira. So the chain was finished rather than left
half-migrated.

**Catalogue (4).** Homepage and `/menu` read `/catalog/*`. Search, filters and all five
sorts run on the server (two were `return 0`). The "Filters" button used to open an
empty overlay; the unmounted `MenuFilters` panel is now that overlay, with dietary tags
from the API and price bands as fixed kobo bounds. Ratings are real or say "No reviews
yet" (every dish showed five stars). The hero's "50+ Popular / 100+ Rated 5★ / 30 min"
were fixed strings and are now counts. The item dialog renders the dish's own sizes and
option groups with real required/up-to-N rules — replacing one `MOCK_CUSTOMIZATIONS`
array on every dish — and its total comes from `POST /cart/quote/`, priced by the same
service the cart charges with. `/menu?item=<slug>` deep-links to a dish; "Share" copies
that link instead of `alert()`.

**Cart (5).** `cartStore` holds the server's cart and nothing it computed; writes are
queued so overlapping responses cannot land out of order. The summary shows server
totals, VAT and delivery notes, price changes and unavailable items since they were
added, and blockers. Checkout stays enabled for blockers resolved *in* checkout (an
address). `promoStore` is deleted — it listed every promo code to every visitor. The
"Frequently Bought Together" panel (hardcoded dishes, dollar-figure prices, a summed
"Add All") shows featured dishes instead. The wishlist stays local until step 10, keyed
by slug; its v1 mock entries are dropped by a persist migration.

**Checkout (6).** Delivery or pickup; signed-in customers pick or add a saved address
(`area` resolves the zone; `landmark` replaces the unused "Zip Code"), and the cart is
re-priced for that zone before review. Payment offers bank transfer only when the
branch has account details. Review shows the server cart, places the order with an
`Idempotency-Key` kept across network retries and `expected_total` as a guard, handles
`price_changed`, and redirects to the provider's hosted page. `/checkout/complete`
verifies by polling the backend — the browser's return is a hint, not proof.

**Orders (7).** `/orders/[id]` renders the event-log timeline (the old one invented
times from the clock), polls every 15 s until a final status while the tab is visible,
and offers pay-now, cancel, receipt PDF and reorder. `/orders` and the account tab read
`/orders/mine/` with a two-line preview. Guests track by the token issued at placement,
kept per reference in this browser. `orderHistoryStore` and the menu image registry are
deleted.

**Product constraints surfaced, not invented around:**

- **Guests can only choose pickup.** Delivery addresses belong to accounts
  (`Address.user` is required and the cart refuses an address for an anonymous cart).
  Checkout offers guests "Sign in for delivery". Allowing guest delivery is a backend
  change and a product decision — see DECISIONS.md OD-7.
- **Bank transfer was a false promise.** The payment step said "You will receive bank
  transfer details after placing your order"; no such details existed anywhere. Branch
  now has bank fields; with any blank, the option is hidden *and* the API refuses a
  transfer order.
- **Cash on delivery is ungated.** PAYMENTS.md §5.3 specifies a cap and a verified
  account; placement does not enforce either. See OD-8.

**Defects found only by running the flow against a live server** (all fixed, all with
regression tests):

| Defect | Effect |
|---|---|
| The dummy payment provider verified every payment as ₦0 | Settlement treated it as an amount-mismatch attack: no simulated card payment could ever succeed in development |
| The verify endpoint built its response from an order cached before settlement | Reported `payment_status: pending` for an order it had just marked paid |
| Cart line items, changes, blockers; order lines, timeline, address, rider were untyped dicts in the schema | The generated client had no types for the screens that matter most |
| A serializer field named `label` shadowed DRF's `Field.label` | Caught by mypy; the wire key is added in `get_fields()` |

Verified: backend 915 passed, ruff/mypy/migrations clean; frontend `tsc` clean,
`next build` passes, ESLint 40 → 33 errors and 12 → 7 warnings with no new findings; a
scripted live run — catalogue, quotes, guest cart, pickup + cash with idempotent replay,
guest token access, transfer refusal, stale-total refusal, register → verify → cart
merge → address → zone-priced delivery → card → verify → paid → receipt → history →
cancel — passes with zero server errors.

**Still to do:** step 8 (account profile, addresses tab, preferences — `ProfileSection`
and `PreferencesSection` still `alert()`, `AddressesSection` still shows two hardcoded
Lagos addresses), wishlist server sync (step 10), reservations/catering/contact wiring,
real menu photographs (none exist — `public/images/menu` is empty), and real prices
(OD-2: 15 of 18 dishes are hidden until repriced).

---

### 5.4 Steps 8 and 10 delivered

**Account (8).** Every tab now reads and writes the account. The old tabs were
fiction shown to every visitor: "John Doe", 1,250 loyalty points, ₦45,600 spent,
Gold tier, "12 orders / 3 addresses / 2 cards / member since 2024", two hardcoded
Lagos addresses, and an "Add New" form whose fields were a code comment.

- *Profile:* name, phone and birthday save to `PATCH /accounts/me/`. Email is shown
  read-only — the backend refuses the change until an email re-verification flow
  exists (AS-5). Password change lives in the sidebar and keeps this session signed
  in. The loyalty card is gone: the programme is Phase 3.
- *Addresses:* list, add, edit, delete, set default, in a Dialog, reusing checkout's
  `AddressForm`. Each shows its delivery zone or "pickup only".
- *Preferences:* only what exists. Marketing consent saves on toggle (withdrawable,
  as NDPR requires); order emails are shown as always on, because they are part of
  the order. The SMS, push, newsletter and four-language controls were removed —
  none existed. Account erasure is here, behind a confirmation.
- *Hero:* real counts of addresses, saved cards and wishlist items, and the real
  join year.

**Wishlist sync.** Signed out, the wishlist stays in this browser. Signing in merges
it into the account (`POST /wishlist/sync/`), which also reports entries that no
longer match a dish; after that, adds and removes are optimistic writes to the
account. Only the signed-out list is persisted, so a shared device never keeps
someone else's account wishlist. `/wishlist` stays open to guests.

**Reservations.** Real availability for the chosen date and party size, replacing
eighteen fixed times shown for every day. Step 2 checks the chosen time against
each seating area and disables areas where it is taken — so the step order is
unchanged and a booking does not fail at the last step. Booking sends an
`Idempotency-Key`, keeps the guest's management token, and ends on a confirmation
with the reference, table and a working cancel. A time taken while the customer
was typing returns them to step 1 with fresh slots. "We'll contact you within
1 hour to confirm" was removed: availability is live and confirmation is
immediate.

**Catering.** Packages, prices and features come from the API. The quote form
submits a real enquiry and shows its reference, the reply-by time and an
indicative total — it used to end in `alert()` and `console.log`. It flags a
guest count outside the chosen package's range.

**Contact.** The form opens a support ticket, carries a hidden honeypot field, and
reports rate limiting in words. Phone, email, address, today's hours, the weekly
schedule and social links come from the branch and site settings; blank social
URLs are hidden rather than linking to `#`. Removed as unverified: a "24/7
hotline: +234 800 KUYASH", directions ("BRT stop 2 minutes walk", "opposite
Federal Palace Hotel"), and eight hardcoded FAQ answers promising valet parking
and a 30-seat private room. The map is built from the branch's own coordinates or
address, and the FAQ from the entries staff maintain in the admin.

**Defect found by the live run:** a contact submission that tripped the honeypot
returned a 500. The quarantine log line passed `extra={"message": ...}`, and
`message` is reserved on Python's `LogRecord`, so building the record raised
`KeyError`. The existing API test passed only because test settings log above INFO,
so that record was never built. Fixed, with a regression test that turns INFO on,
and a static guard (`apps/common/tests/test_logging_extra_keys.py`) that fails the
suite if any log call passes a reserved key — independent of log levels. The bot
now gets the same quiet 201 a person does.

Verified: `tsc` clean; `next build` passes; ESLint 33 → 27 errors and 7 → 2
warnings with no new findings; a live run of site data, reservations (including a
full area refusing a booking rather than double-booking), catering, contact,
profile, password change, addresses, wishlist merge and account erasure passes.

**Still not wired — all Phase 3, with no backend yet:** reviews (`ReviewModal`
still `alert()`s and `console.log`s), academy enrolment (`alert()`), gallery
share/download (`alert()`), and chat (a scripted bot with a 600 ms fake delay;
there are also two copies of `ChatButton`). Menu photographs and real prices are
the restaurant's data to supply (OD-2).

---

## 6. Definition of done for Phase 1 frontend

- [ ] Zero `alert()` calls in any submission path
- [ ] Zero `setTimeout` faking network latency
- [ ] Zero price arithmetic in any component — CI grep gate
- [ ] Zero hardcoded prices, menu items or promo codes
- [ ] Zero card-data fields — CI grep gate
- [ ] Every mutation sends CSRF and `credentials: "include"`
- [ ] Every mutation has loading, error and success states
- [ ] `Idempotency-Key` on order creation
- [ ] Every money value rendered from `Money.display`
- [ ] Auth state is real; protected routes are gated
- [ ] Duplicate component families collapsed to one each
- [ ] `loading.tsx` / `error.tsx` present per route segment
