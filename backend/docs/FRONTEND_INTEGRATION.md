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
npx openapi-typescript https://api.kuyashplace.com/api/v1/schema/ -o lib/api/types.ts
```

Wire this into CI so drift between frontend and backend fails the build rather than production.

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
NEXT_PUBLIC_PAYSTACK_PUBLIC_KEY=pk_live_xxx     # public key only — never the secret
```

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

`app/orders/page.tsx` — read `GET /orders/` instead of the never-written `orderHistoryStore`; route Reorder through `POST /orders/{ref}/reorder/` and surface `removed[]` / `repriced[]`.

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

`/account`, `/orders`, `/wishlist` and `/checkout` are fully public today. Gate them in middleware or a layout guard.

### 4.4 Server Components

`/terms`, `/privacy`, `/cookies`, `/accessibility`, `/refunds`, `/help` and `/about` are marked `"use client"` for no reason. Convert to Server Components fetching from `GET /core/legal/{slug}/`.

---

## 5. Integration order

Follow this sequence; each step is independently shippable.

1. API client, generated types, `authStore`, env vars, `next.config.ts` images
2. **Delete** the dead trees and the card fields (before writing integration code, not after)
3. Auth: login, signup, reset, verify, session bootstrap, route gating
4. Catalogue: menu list, detail, real modifiers, server-side filtering
5. Cart: server cart, server totals, promo application
6. Checkout + payments: order creation, hosted checkout, completion page
7. Orders: tracking with polling, history
8. Account: profile, addresses
9. — **Phase 1 ships here** —
10. Reservations, catering, contact, wishlist sync
11. Academy, rewards, reviews, gallery, chat

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
