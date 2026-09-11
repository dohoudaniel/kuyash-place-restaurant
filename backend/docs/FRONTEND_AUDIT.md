# Frontend Audit — Kuyash Place Restaurant

**Date:** 2026-09-11
**Scope:** `frontend/` at commit `28eb7b3` (branch `dohoudaniel/backend`)
**Method:** full read of all 157 `.ts`/`.tsx` files (16,432 lines) plus config, CSS and data modules.
**Purpose:** establish, with evidence, exactly what the backend has to supply. This is deliberately unflattering. It is not a criticism of the design work — the UI is genuinely good — it is an inventory of the gap between what the screens promise and what the system does.

---

## 0. Executive summary

> The frontend is a high-fidelity prototype that has been mistaken for a product. Roughly **70% of the visible functionality is a promise the system cannot keep.**

The single most important finding:

**There is no network layer at all.** Across the entire codebase there are:

| Thing | Count |
|---|---|
| `fetch()` calls | **0** |
| `axios` / other HTTP clients | **0** |
| Next.js route handlers (`app/api/**`) | **0** |
| Server Actions | **0** |
| Server Components doing data access | **0** (19 of 20 route files are `"use client"`) |
| `alert()` calls standing in for a backend | **18** |
| `setTimeout` calls faking network latency | **15** |
| Data sources | 4 hardcoded TS modules + 4 `localStorage` stores |

Every piece of state that a real restaurant depends on — orders, bookings, enquiries, enrolments, customers, prices — either lives in the customer's own browser or evaporates the moment the modal closes.

**Consequence for planning:** the backend is not "an API layer bolted onto an existing app." The backend is where this application will actually be written for the first time. Budget accordingly.

---

## 1. Features that actively mislead users

These are ranked by real-world harm, not by engineering effort.

### 1.1 Reservations are silently discarded — **Severity: Critical (business)**

`app/reservations/page.tsx:116`

```tsx
onClick={() => {
  if (step < 3) setStep((prev) => (prev + 1) as 1 | 2 | 3);
  else alert("Reservation submitted!");
}}
```

A customer completes a three-step wizard — date, time, party size, table type, name, email, phone, special requests — presses **"Confirm Reservation"**, receives an unambiguous success message, and **nothing is recorded anywhere**. No email, no database row, no console log. The restaurant has no idea they are coming.

This is materially worse than having no booking feature. A missing feature sends the customer to the phone; a fake one sends them to an empty table on their anniversary.

### 1.2 Catering enquiries are discarded — **Severity: Critical (business)**

`app/catering/page.tsx:89`

```tsx
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  alert("Thank you! We'll contact you within 24 hours with a detailed quote.");
  console.log("Catering Quote Request:", formData);
};
```

The Luxury package is **₦12,000 per head, 100–500 guests** — a ₦1.2M–₦6M enquiry. It goes to `console.log`. The app explicitly promises a callback within 24 hours that no human will ever be prompted to make.

### 1.3 Authentication is theatre — **Severity: Critical**

`components/features/auth/LoginForm.tsx:22-30`

```tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setIsLoading(true);
  // Simulate API call
  setTimeout(() => {
    setIsLoading(false);
    alert("Login successful!");
    onSuccess();
  }, 1000);
};
```

Signup (`SignupForm.tsx:37-45`) and password reset (`ForgotPasswordForm.tsx:18-25`) are the same pattern. Password reset even tells the user *"We've sent a password reset link to {email}"* and *"The reset link will expire in 1 hour for security reasons"* — describing security properties of a system that does not exist.

Social login is honest, at least: `alert("${provider} login - Integration needed")` (`LoginForm.tsx:33`).

**There is no concept of an authenticated user anywhere in the codebase.** Greps for `isAuthenticated`, `isLoggedIn`, `useAuth`, `currentUser`, `session`, `token` return nothing outside of these three form files. `AuthModal` is mounted only in `Navbar.tsx` and its only effect on application state is closing itself.

Everything downstream that *should* be gated — `/account`, `/orders`, `/wishlist`, checkout — is fully public.

### 1.4 Checkout charges nobody and creates nothing — **Severity: Critical**

`app/checkout/page.tsx:44-60`

```tsx
const handleConfirmOrder = () => {
  const orderId = `KYS-${Date.now().toString(36).toUpperCase()}`;
  // In a real app, you would:
  // 1. Send order data to backend API
  // 2. Process payment
  // 3. Create order in database
  // 4. Send confirmation email
  clearCart();
  router.push(`/orders/${orderId}`);
};
```

The order ID is derived from the client clock (collision-prone, enumerable, leaks order timing). The cart is destroyed **before** any persistence attempt, so a failure is unrecoverable. No payment is attempted. No order exists.

### 1.5 Raw card data is collected in React state — **Severity: Critical (compliance)**

`components/features/checkout/PaymentStep.tsx` and `PaymentStepCompact.tsx`

```tsx
const [formData, setFormData] = useState<PaymentData>({
  method: "card",
  cardNumber: "",
  cardName: "",
  cardExpiry: "",
  cardCvv: "",
});
```

Full PAN, cardholder name, expiry and **CVV** are captured into component state and passed to the review step as props.

Today this is "merely" a dark pattern — the data is thrown away. **The danger is the obvious next step.** If anyone wires this existing form to a Django endpoint, Kuyash Place instantly enters **PCI-DSS scope at the hardest tier (SAQ D)**: you would be transmitting and processing raw cardholder data, and CVV storage is prohibited outright under PCI-DSS Req. 3.2.

**This form must be deleted, not connected.** See `PAYMENTS.md`.

### 1.6 The order tracking page is a stage set — **Severity: High**

`app/orders/[id]/page.tsx:38-80`

```tsx
// Simulate fetching order data
function getOrderData(orderId: string): OrderData {
  // In a real app, this would be an API call
  return {
    orderId,
    status: "preparing",
    items: [ { name: "Classic Burger", price: 14.90, quantity: 2 }, ... ],
    deliveryAddress: { fullName: "John Doe", phone: "+1 555 123 4567", ... },
    pricing: { subtotal: ..., deliveryFee: 5.00, tax: 2.75, total: ... },
  };
}
```

The `orderId` parameter is accepted and then **ignored except as a display string**. Every order ever "placed" shows the same two items, the same John Doe, the same US phone number, and is permanently stuck at `preparing`.

### 1.7 Two order screens read from two different, never-reconciled sources — **Severity: High**

| Screen | Source | Written by |
|---|---|---|
| `/orders/[id]` | hardcoded `getOrderData()` | nothing |
| `/orders` | `useOrderHistoryStore` (localStorage) | **nothing** |

`orderHistoryStore.ts` is a complete, persisted store with statuses, addresses, pricing and reorder support — and **no code path anywhere writes to it.** Checkout doesn't. So `/orders` is permanently empty while `/orders/[id]` is permanently populated. The two pages are structurally incapable of agreeing.

`/orders` also offers **Reorder**, which clears the cart and re-adds historical items — a destructive action driven entirely by data that cannot exist.

### 1.8 `/account` shows the same fictional person to everyone — **Severity: High**

`components/features/account/ProfileSection.tsx:7-18`

```tsx
const [formData, setFormData] = useState({
  name: "John Doe",
  email: "john@example.com",
  phone: "+234 123 456 7890",
  birthday: "1990-01-15",
});
const handleSave = () => { setIsEditing(false); alert("Profile updated successfully!"); };
```

`AddressesSection.tsx` hardcodes two Lagos addresses. `PaymentMethodsSection.tsx` hardcodes a Visa •4242 and a Mastercard •5555. `PreferencesSection.tsx` saves via `alert()`.

Every visitor sees an identical, fabricated account. Editing anything reports success and changes nothing — not even in local state, in the case of profile.

### 1.9 Reviews and enrolments — **Severity: Medium–High**

- `ReviewModal.tsx:50` — `alert("Thank you for your review! It will be published after moderation.")` then `console.log`. There is no moderation queue and no review will ever appear.
- `EnrollmentModal.tsx:24` — `alert("Enrollment submitted successfully!")`. Courses cost **₦40,000–₦75,000**. The enrolment is discarded, including the chosen start date and payment method (which offers **"installment"** — a financing option with no ledger behind it).
- `ContactForm.tsx:17-21` — sets `submitted = true`, shows a success state, resets after 3s. The message is never even placed in a variable that leaves the component.
- `app/rewards/page.tsx:22` — "Join Free Now" sets `signedUp = true` in local state. Refresh the page and you are not a member. Points, tiers and birthday rewards are marketing copy with no ledger.

### 1.10 Miscellaneous dead buttons

`alert("Share functionality")` in `GalleryGrid.tsx:89`, `ImageLightbox.tsx:146`, `MenuItemDetailModal.tsx:179`; `alert("Download functionality")` in `ImageLightbox.tsx:153`.

---

## 2. Money is wrong — the most dangerous category

### 2.1 Two currencies are wearing the same symbol

| Source | Value | Plausible as ₦? |
|---|---|---|
| `lib/data/menu.ts` — Signature Grill Plate | ₦14.90 | **No** — this is a USD price |
| `lib/data/menu.ts` — Classic Smash Burger | ₦10.90 | **No** |
| `CartSummary.tsx:22` — delivery fee | ₦5.00 | **No** |
| `PaymentStepCompact.tsx:35-40` — tip options | ₦2 / ₦5 / ₦10 | **No** |
| `app/orders/[id]/page.tsx:76` — tax | ₦2.75 | **No** |
| `app/catering/page.tsx` — per head | ₦3,500 / ₦6,500 / ₦12,000 | **Yes** |
| `app/academy/page.tsx` — courses | ₦40,000 – ₦75,000 | **Yes** |

The entire ordering flow was priced in dollars and had the naira glyph swapped in. Catering and academy were priced natively in naira. **Nothing in the codebase reconciles the two**, and a user can put a ₦14.90 burger and a ₦50,000 course in front of the same checkout.

The leak is visible on screen — `components/features/cart/CartSummaryCompact.tsx:52`:

```tsx
<p className="text-[10px]">on orders $25+</p>
```

A literal dollar sign in production copy.

### 2.2 Prices are strings, parsed with a regex, into floats

`lib/types/index.ts`:

```ts
export interface MenuItem {
  price: string;   // "₦14.90"
}
```

`components/features/menu/MenuItem.tsx:27`:

```tsx
const priceValue = parseFloat(item.price.replace(/[^\d.]/g, ""));
```

Three compounding problems:

1. **Money as `float`.** `0.1 + 0.2 !== 0.3`. Totals accumulate error across line items, discounts, VAT and tips.
2. **Money as a display string in the model.** Currency, formatting and value are fused, so the number cannot be summed without being torn apart by a regex.
3. **The regex is lossy.** `replace(/[^\d.]/g, "")` on a thousands-separated price like `"₦14,900.00"` yields `"14900.00"` by luck, but `"₦1.4k"` or any locale variant would silently produce garbage. It also strips minus signs, so a negative adjustment becomes positive.

The wishlist repeats the same parse independently (`app/wishlist/page.tsx:16`), so the two can drift.

### 2.3 VAT, discounts and delivery fees are computed in the browser

`components/features/cart/CartSummary.tsx:21-24`

```tsx
const discount = calculateDiscount(subtotal);
const deliveryFee = appliedPromo?.type === "freeDelivery" ? 0 : subtotal > 0 ? 5.00 : 0;
const tax = (subtotal - discount) * 0.075;   // 7.5% VAT
const total = subtotal - discount + deliveryFee + tax;
```

Every commercial term is client-side and therefore **user-controlled**. Anyone with devtools sets their total to ₦0. There is no server to disagree, because there is no server.

### 2.4 Promo codes ship to the client with their rules

`lib/store/promoStore.ts:25-26`

```ts
// Mock promo codes - in real app, these would come from backend
const AVAILABLE_PROMOS: PromoCode[] = [
  { code: "WELCOME10", type: "percentage", value: 10, ... },
  ...
];
```

The codes, their types, values, minimum order values, caps, expiry dates and `usageLimit`/`usedCount` fields are all in the JavaScript bundle. `usageLimit` is decorative — there is no counter that survives a page refresh, and the UI even *lists the available promos* to the user.

### 2.5 The site contradicts itself about tax — a consumer-protection problem

`app/help/page.tsx:120`:

> "Yes, all displayed prices include applicable taxes. The price you see is the price you pay (plus delivery if applicable)."

`app/terms/page.tsx:47`:

> "All prices are in Nigerian Naira (₦) and include applicable taxes unless otherwise stated."

And yet `CartSummary.tsx:23` adds **7.5% VAT on top** at checkout.

Published terms state tax-inclusive pricing; the cart charges tax-exclusive pricing. Under the FCCPA 2018 that is a misleading price representation, not a styling nit. **The backend must be the single authority on whether displayed prices are VAT-inclusive, and the copy must be corrected to match.** See `PRD.md` §"Pricing and tax policy".

### 2.6 Fee logic is duplicated and already divergent

The identical delivery/VAT/total block is copy-pasted into `CartSummary.tsx` and `CartSummaryCompact.tsx`. `ReviewStep.tsx` and `ReviewStepCompact.tsx` recompute it again, and `app/orders/[id]/page.tsx` hardcodes a *third* set of numbers (`deliveryFee: 5.00, tax: 2.75`) that do not derive from the items shown. Three implementations of one calculation, already disagreeing.

---

## 3. The data model does not survive contact with reality

### 3.1 Product identity is derived from an image filename

`components/features/menu/MenuItem.tsx:28`

```tsx
const itemId = item.imageKey || item.name.toLowerCase().replace(/\s+/g, "-");
```

The cart, wishlist and order-history primary key is **the image registry key**, falling back to a slug of the display name.

Consequences:
- An item with no photo has an ID that changes when marketing renames the dish — silently orphaning every cart, wishlist entry and historical order row.
- Two dishes sharing a photo share an identity and merge in the cart.
- Product identity is coupled to an asset pipeline (`lib/assets/images.ts`), so adding a photo can change an ID.

### 3.2 Customisations are fake and applied universally

`components/features/menu/MenuItemDetailModal.tsx:23`

```tsx
const MOCK_CUSTOMIZATIONS: Customization[] = [ ... ];
```

One hardcoded array of modifiers is rendered for **every** menu item. Pancakes are offered extra cheese. Required-option validation (`line 107`) runs against this fictional set, so the "Please select all required options" gate is meaningless. Selected customisations are appended to the cart item as a `string[]` with **no price effect** — a ₦2,000 protein upgrade costs nothing.

### 3.3 Ratings and sorting are stubs

`components/features/menu/MenuItem.tsx` renders five filled stars and the literal text `5.0` for every dish. `app/menu/page.tsx:81-106`:

```tsx
// Mock: all items have 5.0 rating for now
...
case "rating":  return 0; // Mock: all have same rating
case "newest":  return 0; // Mock: no date property
```

Two of the five sort options are no-ops. The "minimum rating" filter can never exclude anything. The dietary filter is a comment: `// Mock: would filter based on item dietary properties`.

### 3.4 Everything an operating restaurant needs is absent

The menu model is `{ name, description, price, imageKey }`. There is no representation of:

- stock / sold-out state, or per-day availability
- opening hours, or whether the kitchen is currently accepting orders
- preparation time (yet the UI promises "30–45 mins")
- allergens or dietary attributes (yet there is a dietary filter)
- calories/nutrition
- category ordering, featured flags, or seasonal availability
- variants (size, protein choice) or priced modifiers
- tax class per item (some items may be zero-rated)

### 3.5 Reservations have no inventory

`components/features/reservations/TableSelection.tsx` offers three *categories* — indoor, outdoor, private — not tables. `app/reservations/page.tsx` hardcodes 18 time slots from 11:00 to 22:00 and offers party sizes up to 20.

There is no table count, no capacity, no turn time, no blackout dates, no holiday calendar. Every slot is always available because nothing can ever be booked. Double-booking is impossible only because booking is impossible.

### 3.6 Academy, gallery and catering content is hardcoded in page components

- `app/academy/page.tsx:28` — a `COURSES: Course[]` literal, including instructor names, ratings and enrolled-student counts, inside a route file. `CourseGrid.tsx` imports the `Course` type **from the page** (`@/app/academy/page`), inverting the dependency direction.
- `app/gallery/page.tsx:20` — 20 `GALLERY_IMAGES` with `imageKey`s (`"jollof"`, `"suya"`, …) that **do not exist in `lib/assets/images.ts`** — the grid renders a placeholder icon for all 20.
- `app/catering/page.tsx:16` — three packages with prices and feature lists inline.

None of this is editable by the restaurant. Changing a price or a course start date is a code deploy.

---

## 4. Engineering debt the backend team will inherit

These do not block the backend, but they will slow every integration PR.

### 4.1 1,639 inline `style={{}}` objects

The project has a well-formed Tailwind v4 theme in `app/globals.css` (`@theme inline` exposing `--color-red`, `--color-off-white`, …) and the components almost entirely bypass it:

```tsx
<h2 style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
```

Effects: no dark mode (despite `@custom-variant dark` being declared), no hover/focus/responsive variants on any styled property, no design-token enforcement, larger DOM payload, and a rebrand means touching 1,639 sites.

### 4.2 Six dead or duplicated component trees (~1,200 unreachable lines)

| Legacy | Superseded by | Reachable from a route? |
|---|---|---|
| `components/layout/` | `components/layouts/` | No |
| `components/menu/` (`MenuBoard` 354 lines) | `components/features/menu/` | No |
| `components/hero/` | `components/features/hero/` | No |
| `components/stats/` | `components/features/stats/` | No |
| `components/why/` | `components/features/why-choose-us/` | No |
| `components/academy/` | `components/features/academy/` | No |
| `MenuItemDetailModal.old.tsx` (299 lines) | `MenuItemDetailModal.tsx` | No |

Only the two orphans `components/hero/HeroSection.tsx` and `components/academy/AcademyHero.tsx` reference `components/layout/Navbar` — dead code keeping dead code alive.

### 4.3 Three parallel implementations of the same features

Menu exists as flat (`features/menu/*`), advanced (`features/menu/advanced/*`) and legacy (`components/menu/*`). Cart and checkout exist as standard and `*Compact` variants with **divergent logic** — and the app uses them inconsistently: `app/cart` uses the Compact family, `app/checkout` uses the standard one. A fix applied to one is not applied to the other.

### 4.4 A live rendering bug in checkout

`app/checkout/page.tsx:88`

```tsx
{currentStep === 2 && paymentData === null && (
  <PaymentStep onNext={handlePaymentNext} onBack={() => setCurrentStep(1)} />
)}
```

Once `paymentData` is set, returning to step 2 renders **nothing**. Press "Back" on the Review step and the user gets a blank page with no way forward. Reproducible in under 30 seconds.

Related: the step-3 guard requires both `deliveryData` and `paymentData`, and neither survives a refresh, so reloading mid-checkout dumps the user into an empty shell.

### 4.5 Accessibility

Modals (`AuthModal`, `EnrollmentModal`, `ReviewModal`, `MenuItemDetailModal`, `ImageLightbox`) are raw `<div>`s with:

- no `role="dialog"` / `aria-modal`
- no focus trap and no focus restoration
- no Escape-to-close
- backdrop click handled via `onClick` on a non-interactive element

Checkboxes in `SignupForm.tsx` are `<div onClick>` inside a `<label>` — not keyboard reachable, not announced, and the click handler on the inner div means the label's own click can double-toggle.

`shadcn/ui` primitives (`dialog.tsx`, `sheet.tsx`, `select.tsx`, `tabs.tsx`) — which solve all of this — are installed and largely unused.

### 4.6 Other

- `"use client"` on 19 of 20 routes forfeits streaming, RSC data fetching and SEO for pages that are almost entirely static (`/terms`, `/privacy`, `/cookies`, `/accessibility`, `/refunds`, `/help`, `/about`).
- `8` uses of `as any`, mostly to cast `<button>` values into union types — each one a place a typo becomes a runtime bug.
- No `next/image` remote patterns configured (`next.config.ts` is empty) — a blocker the moment images come from Supabase Storage.
- No tests, no test runner, no CI.
- No error boundaries, no `loading.tsx`, no `error.tsx`, no `not-found.tsx` anywhere in `app/`.
- No environment variable usage at all — nothing is configurable per environment.
- `zustand` `persist` stores are read during render without an `isHydrated` guard, which will produce React hydration mismatches once server rendering actually matters.

---

## 5. What is genuinely good (and worth preserving)

An audit that only lists faults is not useful for planning. These are real assets:

- **Visual design and information architecture.** The page inventory is thoughtful and complete; the red/black/off-white system is coherent; Playfair + Inter is a strong pairing.
- **`components/features/<domain>/` with `index.ts` barrels** is a sound convention. Keep it; finish migrating into it.
- **`lib/types/index.ts`** is a real, if thin, shared type layer — the natural place to land generated API types.
- **The zustand stores are well-shaped.** `cartStore`, `wishlistStore` and `orderHistoryStore` have sensible interfaces. `cartStore` in particular can stay almost as-is as an optimistic local cache in front of a server cart.
- **Tailwind v4 theme tokens in `globals.css`** are correctly defined — the components simply need to start using them.
- **The checkout and reservation wizards** are good UX skeletons. The step flow, progress indicator and summary sidebar are all keepers; only the data handling is missing.

---

## 6. Feature-by-feature backend requirement matrix

| Frontend surface | Current behaviour | Backend needed | Phase |
|---|---|---|---|
| Login / Signup / Reset | `alert()` + `setTimeout` | allauth session auth, email verification, password reset | 1 |
| Google / Facebook login | `alert("Integration needed")` | allauth socialaccount providers | 2 |
| Menu browse | 18 items in `lib/data/menu.ts` | `catalog` app: categories, items, variants, modifiers, availability, media | 1 |
| Menu search / filter / sort | Client-side; rating & newest are no-ops | Server-side filtering, real ratings, `created_at`, dietary tags | 1–2 |
| Item customisation | `MOCK_CUSTOMIZATIONS` for all items | Per-item modifier groups with price deltas | 1 |
| Cart | localStorage, client-priced | Server cart with authoritative repricing | 1 |
| Promo codes | Shipped in JS bundle | `promotions` app: server validation, redemption ledger, usage caps | 1 |
| VAT / delivery fee | `* 0.075` in the browser | Server-computed totals; item tax classes; zone-based delivery | 1 |
| Checkout | Generates a fake ID, clears cart | Order creation, idempotency, stock/availability checks | 1 |
| Payment | Collects raw PAN + CVV | **Delete form.** Paystack/Flutterwave hosted checkout + webhooks | 1 |
| Order tracking | Hardcoded John Doe order | Real order + status event log, polling endpoint | 1 |
| Order history | Empty store nothing writes to | `GET /orders/`, server-owned | 1 |
| Reorder | Reads the empty store | Server-side reorder with availability revalidation | 2 |
| Account profile | Hardcoded "John Doe" | `accounts` app: profile CRUD | 1 |
| Addresses | Hardcoded array | Address book CRUD + zone resolution | 1 |
| Saved payment methods | Hardcoded Visa •4242 | Provider-tokenised cards (authorization codes only) | 2 |
| Preferences | `alert()` | Notification/dietary preferences | 2 |
| Wishlist | localStorage only | Server-synced wishlist for logged-in users | 2 |
| Reservations | `alert()` | `reservations` app: tables, slots, capacity, confirmation email | 2 |
| Catering | `console.log` | `catering` app: packages, enquiries, quotes, staff workflow | 2 |
| Contact form | Local state only | `support` app: messages → ticket queue | 2 |
| Reviews | `alert()` + `console.log` | `reviews` app: verified-purchase reviews, moderation, aggregates | 3 |
| Academy | Courses inline in the page | `academy` app: courses, cohorts, enrolments, payment, certificates | 3 |
| Rewards | `useState(false)` | `loyalty` app: points ledger, tiers, redemptions | 3 |
| Gallery | 20 items, broken image keys | `gallery` app + Supabase Storage | 3 |
| Chat widget | Local echo | `support` app: scripted FAQ + ticket handoff | 3 |
| Legal pages | Static, contradictory | `cms` app: editable pages, corrected tax copy | 2 |
| Homepage stats | Hardcoded numbers | `cms` singleton or computed metrics | 3 |

---

## 7. Prioritised remediation list for the frontend

Independent of the backend, these should be fixed. Ordered by (harm ÷ effort).

**Do immediately — before any further demo:**

1. Disable or clearly mark as non-functional every `alert()`-backed submission (reservations, catering, contact, reviews, enrolment, auth). A "coming soon" state is honest; a fake success is not.
2. **Delete the card-number form fields.** They must never be connected.
3. Fix the blank-page bug at `app/checkout/page.tsx:88`.
4. Remove the `$25+` string at `CartSummaryCompact.tsx:52`.
5. Reconcile the tax copy in `help` and `terms` with actual behaviour.

**Do during Phase 1 integration:**

6. Delete the six dead component trees and `MenuItemDetailModal.old.tsx`.
7. Collapse `Compact`/standard/`advanced` duplicates to one implementation each.
8. Move all pricing arithmetic out of components; render server-supplied totals only.
9. Introduce a typed API client and generated types from the OpenAPI schema.
10. Add an auth store/provider and gate `/account`, `/orders`, `/wishlist`, `/checkout`.
11. Add `loading.tsx` / `error.tsx` / `not-found.tsx` per route segment.
12. Add an `isHydrated` guard to persisted zustand stores.

**Do as capacity allows:**

13. Migrate inline `style={{}}` to Tailwind tokens, starting with the most-edited components.
14. Replace hand-rolled modals with the installed `shadcn/ui` `Dialog`/`Sheet`.
15. Convert static legal/marketing routes to Server Components.
16. Configure `next/image` `remotePatterns` for the Supabase Storage domain.
17. Introduce Vitest + Testing Library and a CI lint/typecheck/test gate.

---

## 8. Evidence index

Every claim above is anchored to a file. Quick reference for the highest-severity items:

| Finding | Location |
|---|---|
| Fake login | `frontend/components/features/auth/LoginForm.tsx:22` |
| Fake signup | `frontend/components/features/auth/SignupForm.tsx:37` |
| Fake password reset | `frontend/components/features/auth/ForgotPasswordForm.tsx:18` |
| Raw PAN/CVV capture | `frontend/components/features/checkout/PaymentStep.tsx`, `PaymentStepCompact.tsx` |
| Fake order creation | `frontend/app/checkout/page.tsx:44` |
| Hardcoded order | `frontend/app/orders/[id]/page.tsx:38` |
| Unwritten order store | `frontend/lib/store/orderHistoryStore.ts` |
| Hardcoded profile | `frontend/components/features/account/ProfileSection.tsx:7` |
| Discarded reservation | `frontend/app/reservations/page.tsx:116` |
| Discarded catering lead | `frontend/app/catering/page.tsx:89` |
| Discarded review | `frontend/components/features/reviews/ReviewModal.tsx:50` |
| Discarded enrolment | `frontend/components/features/academy/EnrollmentModal.tsx:24` |
| Client-side VAT | `frontend/components/features/cart/CartSummary.tsx:23` |
| Client-side promos | `frontend/lib/store/promoStore.ts:25` |
| Float money parse | `frontend/components/features/menu/MenuItem.tsx:27` |
| `$25+` leak | `frontend/components/features/cart/CartSummaryCompact.tsx:52` |
| Tax copy contradiction | `frontend/app/help/page.tsx:120`, `frontend/app/terms/page.tsx:47` |
| Mock customisations | `frontend/components/features/menu/MenuItemDetailModal.tsx:23` |
| No-op sorting | `frontend/app/menu/page.tsx:104` |
| Checkout blank page | `frontend/app/checkout/page.tsx:88` |
