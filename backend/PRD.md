# Product Requirements Document — Kuyash Place Restaurant Backend

**Version:** 1.0
**Date:** 2026-09-11
**Status:** Approved for build
**Owner:** dohoudaniel
**Stack:** Django 5.x + Django REST Framework + PostgreSQL + Redis + Celery

---

## 1. Why this document exists

The `frontend/` application is a 16,432-line prototype with **no network layer** — zero `fetch()` calls, zero API routes, zero server actions. Orders, reservations, catering enquiries, reviews, enrolments and user accounts are all simulated with `alert()` and `setTimeout`. Prices, VAT, discounts and delivery fees are computed in the browser from hardcoded string literals.

A full evidence-based teardown is in [`docs/FRONTEND_AUDIT.md`](docs/FRONTEND_AUDIT.md). Read it before this document.

**The implication that governs everything below:** this is not an API being added to a working application. This is the application being written for the first time. The frontend is the specification of the user experience; the backend is the specification of the system.

---

## 2. Product vision

Kuyash Place Restaurant is a single-location Nigerian restaurant in Lagos operating five commercial lines:

1. **Food ordering** — delivery and pickup, the revenue core
2. **Table reservations** — dine-in bookings
3. **Catering** — high-value event enquiries (₦3,500–₦12,000 per head, 10–500 guests)
4. **Culinary academy** — paid courses (₦40,000–₦75,000)
5. **Loyalty** — points, tiers, retention

The backend must make all five real, correct and operable by non-technical restaurant staff, with money handled to the standard a real business requires.

### 2.1 Product principles

| # | Principle | What it forbids |
|---|---|---|
| P1 | **The server is the only authority on money.** | Any price, discount, fee, tax or total calculated in the browser and trusted. |
| P2 | **No action reports success unless it persisted.** | `alert("Reservation submitted!")` with no row written. |
| P3 | **Cardholder data never touches our infrastructure.** | The existing PAN/CVV form. Hosted provider checkout only. |
| P4 | **Staff change content and prices, not developers.** | Menu items, prices, courses, packages or hours living in code. |
| P5 | **Model for one branch, design for many.** | A schema that cannot grow a second outlet without a rewrite. |
| P6 | **Every state change is auditable.** | Order status mutated in place with no event trail. |

---

## 3. Decisions taken (agreed 2026-09-11)

These were resolved with the product owner before writing. Full rationale in [`docs/DECISIONS.md`](docs/DECISIONS.md).

| Area | Decision |
|---|---|
| **Build strategy** | Phased. Phase 1 = ordering core. Phase 2 = reservations, catering, contact, addresses. Phase 3 = academy, rewards, reviews, gallery, chat. Unbuilt features are hidden or explicitly marked "coming soon" in the UI — never faked. |
| **Payments** | **Paystack** (primary) and **Flutterwave** (secondary), both via hosted/inline checkout with server-side verification and webhooks. Plus bank transfer and cash-on-delivery as order-level payment methods. |
| **Authentication** | **django-allauth with session cookies** (HttpOnly, Secure, SameSite=Lax), same parent domain as the frontend. Social providers (Google, Facebook) in Phase 2. |
| **Realtime** | **Polling first** — `GET /api/v1/orders/{ref}/` every ~15s while an order is active. Django Channels + WebSockets documented as a Phase 3 upgrade. |
| **Staff operations** | **Customised Django admin** for content, pricing, promos and refunds, **plus a purpose-built Kitchen Display System (KDS)** endpoint set and screen for live order handling. |
| **Delivery** | **Own riders, zone-based fees.** Named zones each carry a flat fee, minimum order value and ETA. Riders are staff users assigned to orders. |
| **Pricing** | **Backend is the source of truth.** Prices become integer **kobo** in the database, seeded with clearly-marked `NEEDS_REPRICING` placeholders. The owner sets real naira prices in Django admin before launch. The frontend stops hardcoding prices entirely. |
| **Media** | **Supabase Storage** (S3-compatible) via `django-storages`, for menu photos, gallery, course thumbnails and staff uploads. |
| **Notifications** | **Transactional email only** in Phase 1–2 (order confirmations, password reset, email verification, reservation and catering confirmations, receipts). SMS/WhatsApp deferred. |
| **Chat widget** | **Scripted FAQ bot** answering from a server-managed FAQ set plus order-status lookup, with **handoff to a support ticket** staff see in admin. No AI, no fabricated answers. |
| **Branches** | **Single location, modelled for growth.** A `Branch` table exists with exactly one row; menus, prices, zones, hours and stock hang off it. |
| **Deployment** | Not yet chosen. [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) documents a recommended default (Docker + Postgres + Redis; frontend on Vercel, backend on a managed PaaS) alongside VPS and AWS alternatives. |

---

## 4. Users and roles

| Role | Description | Access |
|---|---|---|
| **Guest** | Unauthenticated visitor | Browse menu/gallery/academy, build a cart, submit contact and catering enquiries, checkout as guest (phone + email required) |
| **Customer** | Registered, email-verified | Everything a guest can do, plus order history, saved addresses, wishlist sync, reservations under their name, loyalty points, reviews on verified purchases |
| **Rider** | Delivery staff | KDS delivery queue, accept assignment, mark picked up / delivered, record cash collected |
| **Kitchen staff** | Front-of-house and kitchen | KDS: view incoming orders, accept/reject, advance status, toggle item availability (86 an item) |
| **Manager** | Restaurant management | All of the above, plus admin: menu and pricing, promo codes, reservations, catering quotes, refunds up to a limit, reports |
| **Admin** | System owner | Full Django admin, user management, settings, unlimited refunds, integration configuration |

Roles are implemented as Django `Group`s with granular permissions, not as a `role` enum column — this keeps permission checks in one place and lets a manager also be a rider on a short-staffed evening.

---

## 5. Functional requirements

Requirements use **MUST / SHOULD / MAY** (RFC 2119). Each carries an ID for traceability to tests.

### 5.1 Catalogue (Phase 1)

- **CAT-1** The system MUST store menu categories with a name, slug, emoji, display order and active flag. *(Replaces `MENU_CATEGORIES` in `lib/data/menu.ts`.)*
- **CAT-2** The system MUST store menu items with name, slug, description, base price in kobo, category, images, display order, active flag, `is_featured`, and `created_at`.
- **CAT-3** Menu items MUST support **variants** (e.g. Regular / Large) each with its own price delta, so that size does not require duplicate items.
- **CAT-4** Menu items MUST support **modifier groups** (e.g. "Choose your protein", "Add extras") attached per item, each with `min_select`, `max_select`, `is_required`, and modifiers carrying a price delta. *(Replaces the global `MOCK_CUSTOMIZATIONS` array which offered extra cheese on pancakes.)*
- **CAT-5** Menu items MUST carry **dietary tags** (vegetarian, vegan, gluten-free, contains-nuts, halal, spicy) so the existing dietary filter stops being a no-op comment.
- **CAT-6** Menu items MUST carry **allergen information** as free text plus structured tags.
- **CAT-7** The system MUST support **availability**: a permanent `is_active` flag, a staff-toggleable `is_available_now` ("86 this item"), and optional day/time windows (e.g. breakfast 07:00–11:00).
- **CAT-8** Menu items MUST carry a `prep_time_minutes` used to compute order ETAs, replacing the hardcoded "30–45 mins" copy.
- **CAT-9** Menu items MUST carry a **tax class** (standard 7.5% VAT / zero-rated / exempt) rather than a flat site-wide rate.
- **CAT-10** The system MUST expose aggregate **rating** (`average_rating`, `review_count`) computed from real reviews, replacing the hardcoded `5.0` on every card.
- **CAT-11** The catalogue API MUST support search, category filter, dietary filter, price range, minimum rating, and sorting by popularity, price (asc/desc), rating and newest — all server-side. *(Two of these five sorts are currently `return 0`.)*
- **CAT-12** Prices MUST be stored as **integer kobo** (`PositiveBigIntegerField`), never as floats or strings.
- **CAT-13** All seeded prices MUST be flagged `needs_repricing=True` until a manager confirms them, and the admin MUST surface an unmissable warning listing unconfirmed items.

### 5.2 Accounts and authentication (Phase 1)

- **AUTH-1** The system MUST support email+password registration with **mandatory email verification** before an account is considered active.
- **AUTH-2** Login MUST establish an HttpOnly, Secure, SameSite=Lax session cookie. No token is ever readable by JavaScript.
- **AUTH-3** Password reset MUST send a single-use, time-limited (1 hour) token by email — matching the promise the current UI already makes.
- **AUTH-4** Passwords MUST be validated against Django's validators plus a minimum length of 10 (the UI currently claims 8; we raise it and update the copy).
- **AUTH-5** Authentication endpoints MUST be rate-limited (see SEC-4).
- **AUTH-6** The system MUST support **guest checkout** — an order keyed to email + phone with no account — and MUST offer to claim those orders on later registration with the same email.
- **AUTH-7** Users MUST be able to read and update their profile: full name, email (re-verification on change), phone, date of birth, marketing opt-in.
- **AUTH-8** Users MUST have an **address book** with a label (home/work/other), recipient name, phone, street, city, state, landmark, delivery notes, resolved delivery zone, and a default flag.
- **AUTH-9** Account deletion MUST be supported (NDPR right to erasure), anonymising rather than deleting financial records.
- **AUTH-10** *(Phase 2)* Google and Facebook social login MUST be supported via allauth, wiring up the two buttons that currently say "Integration needed".

### 5.3 Cart and pricing (Phase 1)

- **CART-1** The system MUST maintain a **server-side cart**, keyed to the user for authenticated sessions and to an anonymous cart token for guests.
- **CART-2** On login, an anonymous cart MUST be merged into the user's cart.
- **CART-3** Cart line items MUST reference a menu item **by stable UUID/slug**, never by image key or name slug. *(Currently `itemId = item.imageKey || slugify(name)` — renaming a dish orphans every cart.)*
- **CART-4** Cart line items MUST capture chosen variant and modifiers, and modifiers MUST affect the line price.
- **CART-5** The server MUST be the sole calculator of: line subtotals, order subtotal, promo discount, delivery fee, VAT, service charge (if any), tip and grand total.
- **CART-6** Every price returned to the client MUST be accompanied by a **formatted display string** generated server-side, so the frontend never formats currency.
- **CART-7** The cart MUST be **repriced on every read**. If a menu price changed or an item became unavailable since the item was added, the response MUST include explicit `changes[]` and `unavailable[]` arrays for the UI to surface.
- **CART-8** The API MUST never accept a price, discount or total from the client. Any such field in a request body MUST be ignored.

### 5.4 Promotions (Phase 1)

- **PROMO-1** Promo codes MUST live server-side only. *(Currently the full rule set including usage limits ships in the JS bundle.)*
- **PROMO-2** Codes MUST support: percentage discount, fixed-amount discount, free delivery, and buy-X-get-Y *(Phase 3)*.
- **PROMO-3** Codes MUST support constraints: minimum order value, maximum discount cap, valid-from/valid-until, total usage limit, per-customer usage limit, first-order-only, and applicable categories/items.
- **PROMO-4** Every application MUST be recorded in a **redemption ledger** so usage limits are actually enforceable and reversible on refund.
- **PROMO-5** Validation MUST happen both at apply-time and again at order-placement time; a code that expired between the two MUST fail the order cleanly with a clear message.
- **PROMO-6** The API MUST NOT enumerate available promo codes to customers. *(The current cart UI lists them.)*

### 5.5 Orders and fulfilment (Phase 1)

- **ORD-1** Order references MUST be server-generated, non-sequential and non-enumerable (e.g. `KYS-` + base32 of a random value). *(Currently `KYS-${Date.now().toString(36)}` — client-generated, collision-prone and leaks timing.)*
- **ORD-2** Order creation MUST be **idempotent** via a client-supplied `Idempotency-Key` header, so a double-tap or retry never creates two orders or two charges.
- **ORD-3** An order MUST snapshot, at creation time: item names, descriptions, unit prices, variant and modifier selections and their prices, delivery address, and every pricing component. Later catalogue edits MUST NOT alter historical orders.
- **ORD-4** The cart MUST NOT be cleared until an order has been successfully persisted. *(Currently cleared before any persistence attempt.)*
- **ORD-5** Orders MUST support fulfilment types: **delivery** and **pickup**.
- **ORD-6** Orders MUST support payment methods: **card** (Paystack/Flutterwave), **bank transfer**, **cash on delivery**.
- **ORD-7** Orders MUST follow an explicit state machine with only legal transitions permitted (see [`docs/ORDERS_AND_FULFILMENT.md`](docs/ORDERS_AND_FULFILMENT.md)):
  `pending_payment → paid → confirmed → preparing → ready → out_for_delivery → delivered`, with `rejected`, `cancelled`, `refunded` and `failed` branches.
- **ORD-8** Every transition MUST be written to an append-only `OrderStatusEvent` log with actor, timestamp, from-state, to-state and optional note.
- **ORD-9** The customer-facing status endpoint MUST be cheap enough to poll every 15 seconds and MUST support `ETag`/`If-None-Match`.
- **ORD-10** Customers MUST be able to cancel an order only while it is `paid` or `confirmed`; after `preparing` cancellation requires staff action.
- **ORD-11** Orders MUST compute and expose an **ETA** derived from item prep times, current kitchen load and the delivery zone's estimated minutes.
- **ORD-12** Order history MUST be server-owned and paginated. *(Currently a localStorage store nothing writes to.)*
- **ORD-13** *(Phase 2)* Reorder MUST rebuild a cart server-side, revalidating availability and current prices, and MUST report what changed.

### 5.6 Payments (Phase 1)

- **PAY-1** The system MUST NOT accept, transmit, log or store raw card numbers, expiry dates or CVVs under any circumstance. **The existing card form must be deleted, not connected.**
- **PAY-2** Card payments MUST use Paystack or Flutterwave **hosted or inline checkout**, where the card data goes directly from the customer's browser to the provider.
- **PAY-3** Payment success MUST be established by **server-side verification** against the provider API and/or a signature-verified webhook — **never** by trusting a client-side callback.
- **PAY-4** Webhook endpoints MUST verify provider signatures (Paystack `x-paystack-signature` HMAC-SHA512; Flutterwave `verif-hash`) and MUST be idempotent against duplicate deliveries.
- **PAY-5** The verified amount and currency MUST be checked against the order's expected total; a mismatch MUST NOT mark the order paid and MUST raise an alert.
- **PAY-6** Every payment attempt MUST be recorded as a `PaymentTransaction` with provider, provider reference, amount, currency, status, raw payload and timestamps.
- **PAY-7** Refunds (full and partial) MUST be supported through the provider API, recorded, and MUST reverse any loyalty points and promo redemptions.
- **PAY-8** Cash-on-delivery orders MUST track `amount_collected` by the rider and reconcile at shift end.
- **PAY-9** Bank transfers MUST be confirmable by staff in admin, with an optional Phase 3 upgrade to dedicated virtual accounts for automatic reconciliation.
- **PAY-10** *(Phase 2)* Saved cards MUST store only the provider's reusable authorization code plus the last four digits, brand and expiry — never the PAN.

### 5.7 Delivery (Phase 1)

- **DEL-1** The system MUST define named **delivery zones** (e.g. Victoria Island, Ikoyi, Lekki Phase 1) each with a flat fee in kobo, a minimum order value, an estimated delivery time and an active flag.
- **DEL-2** An address MUST resolve to a zone; an address outside all zones MUST block delivery checkout with a clear message and offer pickup.
- **DEL-3** Free-delivery thresholds and free-delivery promo codes MUST be applied server-side.
- **DEL-4** Riders MUST be assignable to orders, with assignment, pickup and delivery timestamps recorded.
- **DEL-5** The system MUST enforce **opening hours** and reject orders placed when the kitchen is closed, offering scheduled ordering where configured.

### 5.8 Kitchen Display System (Phase 1)

- **KDS-1** Staff MUST see incoming orders in near-real-time (polling in Phase 1, WebSockets in Phase 3), sorted by placement time with visible elapsed timers.
- **KDS-2** Staff MUST be able to accept or reject an order with a reason; rejection MUST trigger an automatic refund for prepaid orders.
- **KDS-3** Staff MUST be able to advance an order through the state machine with one tap per transition.
- **KDS-4** Staff MUST be able to mark a menu item unavailable ("86") directly from the KDS, immediately removing it from the customer menu.
- **KDS-5** The KDS MUST show item modifiers and special instructions prominently — these are the instructions the kitchen actually cooks from.
- **KDS-6** All KDS actions MUST be permission-gated and attributed to the acting staff user.

### 5.9 Reservations (Phase 2)

- **RES-1** The system MUST model **actual tables** with a number, seating capacity, area (indoor/outdoor/private) and active flag — not just three abstract categories.
- **RES-2** Availability MUST be computed from real capacity: configured service periods, slot interval, turn time per party size, existing bookings, blackout dates and holidays.
- **RES-3** The availability endpoint MUST return only genuinely bookable slots. *(The UI currently hardcodes 18 slots that are always available.)*
- **RES-4** Reservations MUST capture date, time, party size, area preference, guest name, email, phone and special requests, and MUST be linked to a user account when one is present.
- **RES-5** Creating a reservation MUST send a confirmation email containing a cancellation/modification link.
- **RES-6** Double-booking MUST be impossible — allocation MUST use a database-level constraint or row lock, not an application-level check.
- **RES-7** Reservations MUST support statuses: `pending`, `confirmed`, `seated`, `completed`, `cancelled`, `no_show`.
- **RES-8** Staff MUST be able to manage the day's book from admin, including walk-ins.
- **RES-9** Large parties (configurable, e.g. >10) MAY require manual confirmation rather than auto-confirming.

### 5.10 Catering (Phase 2)

- **CAT-E-1** Catering packages MUST be managed in admin: name, description, min/max guests, price per head in kobo, feature list, popular flag, active flag.
- **CAT-E-2** Enquiries MUST persist every field the current form collects: name, email, phone, event type, event date, guest count, chosen package, venue and message.
- **CAT-E-3** Submitting an enquiry MUST send an acknowledgement email to the customer and a notification to the catering inbox.
- **CAT-E-4** Enquiries MUST have a staff workflow: `new → contacted → quoted → won / lost`, with an assignee and internal notes.
- **CAT-E-5** The system MUST compute an indicative total (`guests × price_per_head`) for staff triage, clearly marked as indicative.
- **CAT-E-6** The "we'll contact you within 24 hours" promise MUST be backed by an admin view of overdue enquiries.

### 5.11 Support: contact, FAQ and chat (Phase 2–3)

- **SUP-1** Contact form submissions MUST persist with the reason category the form already collects (general, reservation, catering, feedback, partnership).
- **SUP-2** Each submission MUST create a **ticket** with status, assignee and a reply thread; replies MUST email the customer.
- **SUP-3** Submissions MUST be spam-protected (honeypot + rate limit, optionally Turnstile).
- **SUP-4** FAQ entries MUST be managed in admin and served to both the `/help` page and the chat bot.
- **SUP-5** *(Phase 3)* The chat widget MUST answer from the FAQ set by keyword match, MUST support an **order status lookup** by reference, and MUST convert anything it cannot answer into a support ticket. It MUST NOT invent answers, prices or delivery promises.

### 5.12 Reviews (Phase 3)

- **REV-1** Reviews MUST be linked to a **verified purchase** where possible and flagged as such.
- **REV-2** Reviews MUST carry rating (1–5), title, comment, recommend flag and author.
- **REV-3** Reviews MUST enter a **moderation queue** and only appear publicly once approved — the promise the current UI already makes.
- **REV-4** Approved reviews MUST update the parent item's aggregate rating, replacing the hardcoded `5.0`.
- **REV-5** One review per customer per order line, editable within a configurable window.

### 5.13 Academy (Phase 3)

- **ACA-1** Courses MUST be managed in admin: title, description, instructor, category (beginner→masterclass), type (cooking/baking/plating/business/nutrition), duration, session count, price in kobo, features, thumbnail, active flag.
- **ACA-2** Instructors MUST be a first-class model, not a free-text string.
- **ACA-3** Courses MUST have **cohorts** with a start date, end date, capacity and enrolled count — so "start date" is a real, bounded choice rather than a free-text field.
- **ACA-4** Enrolment MUST capture the student, cohort, experience level and payment, and MUST decrement cohort capacity atomically.
- **ACA-5** Course payment MUST reuse the same payment infrastructure as orders.
- **ACA-6** The **installment** option currently offered in the UI MUST either be backed by a real payment-plan ledger or removed from the UI. It MUST NOT remain as unbacked copy.
- **ACA-7** Enrolment MUST send a confirmation email with cohort details.
- **ACA-8** Ratings and enrolled-student counts MUST be computed, not hardcoded.

### 5.14 Loyalty and rewards (Phase 3)

- **LOY-1** Each customer MUST have a loyalty account with a **points ledger** — append-only entries for earning, redemption, expiry and manual adjustment. A balance column alone is not acceptable.
- **LOY-2** Points MUST accrue on `delivered` orders at a configurable rate (the UI currently promises 1 point per ₦100).
- **LOY-3** Tiers (Silver / Gold / Platinum per the existing UI) MUST be defined in admin with thresholds and benefits, and recalculated on ledger change.
- **LOY-4** Rewards MUST be redeemable for discounts on an order, recorded in the ledger, and reversed if the order is refunded.
- **LOY-5** Points MUST be reversed when an order is refunded or cancelled after accrual.
- **LOY-6** Birthday rewards MUST be issuable automatically from the profile date of birth.

### 5.15 Content management (Phase 2)

- **CMS-1** Site settings MUST be editable: restaurant name, address, phones, emails, social links, map coordinates.
- **CMS-2** Opening hours MUST be editable per day with support for split services and holiday overrides, and MUST drive the "currently accepting orders" check.
- **CMS-3** Legal pages (terms, privacy, cookies, refunds, accessibility) MUST be editable in admin with version history.
- **CMS-4** **The tax copy contradiction MUST be resolved**: `/help` and `/terms` currently state prices are tax-inclusive while the cart adds 7.5% VAT on top. The backend decides the policy; the copy must be updated to match. See §7.
- **CMS-5** Gallery images MUST be managed in admin with category, title, description and tags, stored in Supabase Storage. *(20 gallery items currently reference image keys that do not exist, so all 20 render a placeholder icon.)*
- **CMS-6** Homepage statistics MUST be either editable in admin or computed from real data — not hardcoded.

### 5.16 Notifications (Phase 1)

- **NOT-1** Transactional email MUST be sent for: email verification, password reset, order confirmation, order status changes (confirmed, out for delivery, delivered), order cancellation/refund, reservation confirmation and reminder, catering acknowledgement, contact acknowledgement, academy enrolment confirmation.
- **NOT-2** Email MUST be sent **asynchronously via Celery**, never inline in a request.
- **NOT-3** Every send MUST be recorded with status and provider message ID for support and debugging.
- **NOT-4** Templates MUST be branded and MUST render correctly as plain text as well as HTML.
- **NOT-5** Marketing email MUST respect the opt-in captured at signup and provide one-click unsubscribe.

---

## 6. Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| **NFR-1** | Catalogue read latency (p95) | < 200 ms |
| **NFR-2** | Order creation latency (p95) | < 800 ms excluding provider round-trip |
| **NFR-3** | Order status poll latency (p95) | < 100 ms, `ETag`-cacheable |
| **NFR-4** | Concurrent active orders supported | 200 without degradation |
| **NFR-5** | Availability target | 99.5% monthly |
| **NFR-6** | Database backups | Daily automated, 30-day retention, restore tested quarterly |
| **NFR-7** | API documentation | OpenAPI 3.1 auto-generated (`drf-spectacular`), always in sync |
| **NFR-8** | Test coverage | ≥ 85% overall; **100% on all money, tax, discount, payment and state-machine logic** |
| **NFR-9** | Error tracking | Sentry with release tagging |
| **NFR-10** | Structured logging | JSON logs with request ID correlation |
| **NFR-11** | Migrations | Always reversible; zero-downtime-safe for Phase 2+ |
| **NFR-12** | Timezone | All timestamps stored UTC; `Africa/Lagos` for display and business-hours logic |
| **NFR-13** | Currency | NGN only. All amounts integer kobo. No floats in any money path. |

---

## 7. Pricing and tax policy — a decision the product owner must make

This is called out separately because it is the one open item that is a **business** decision, not a technical one, and it currently exposes the restaurant.

**Current state:** the published terms and help pages say prices include tax; the cart adds 7.5% VAT on top at checkout. These cannot both be true.

**Option A — VAT-inclusive (recommended, and matches the published copy).**
Menu prices are what the customer pays. VAT is computed *out* of the price for accounting (`vat = total × 7.5 / 107.5`) and shown as a memo line. No surprise at checkout. No copy changes needed. This is the norm for Nigerian restaurant menus.

**Option B — VAT-exclusive.**
Menu prices exclude VAT; 7.5% is added at checkout. Matches the current cart behaviour, but **the terms, help and refunds pages must be rewritten** and every price display must carry an "excl. VAT" qualifier.

The backend supports either via a `Branch.prices_include_vat` flag and per-item tax classes. **The data model and API are identical; only the calculation direction and the copy change.** Until this is answered, Phase 1 will be built with Option A as the default.

> **Action required from the product owner.** Confirm A or B before the pricing engine is finalised.

---

## 8. Out of scope

Explicitly not being built, to prevent scope drift:

- Native mobile applications
- Third-party delivery aggregator integration (Glovo, Chowdeck, etc.)
- POS / till integration
- Inventory and stock-depletion management (beyond the manual "86 this item" toggle)
- Payroll, HR or staff scheduling
- Multi-currency
- Table-side QR ordering
- Franchise / multi-tenant separation (single-tenant, branch-ready only)
- AI chat (explicitly rejected in favour of the scripted FAQ bot)
- SMS and WhatsApp notifications (deferred)

---

## 9. Success criteria

Phase 1 is done when **all** of the following are true:

1. A customer can register, verify their email, sign in, and see their own name — not "John Doe".
2. A customer can browse a menu whose prices, availability and photos are set by staff in Django admin.
3. A customer can add items with real, priced modifiers to a cart that survives switching devices.
4. Every figure on the cart and checkout screens — subtotal, discount, delivery, VAT, tip, total — comes from the server, and tampering with the client changes nothing.
5. A promo code validates server-side, respects its usage limits, and cannot be enumerated from the browser.
6. A customer pays through Paystack or Flutterwave hosted checkout and **no card data ever reaches our servers**.
7. An order exists in the database with a server-generated reference before the cart is cleared.
8. Kitchen staff see that order on the KDS within 15 seconds and can advance it through to delivered.
9. The customer sees each status change on `/orders/{ref}` and receives emails at confirmation and dispatch.
10. The order appears in a real, server-backed order history.
11. **Zero `alert()` calls remain in any submission path.** Anything not yet built is visibly and honestly marked "coming soon".

Phase 2 and Phase 3 criteria are in [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## 10. Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| The card form is wired to an endpoint instead of deleted | Catastrophic — PCI-DSS SAQ D exposure, card-brand fines | Medium | Delete the fields in the first integration PR; add a CI grep that fails the build on `cardNumber`/`cardCvv` |
| Menu prices launch unrepriced (₦14.90 burgers) | Severe revenue loss | **High** | `needs_repricing` flag, an admin banner, and a launch checklist gate that blocks go-live |
| Tax policy stays ambiguous | Regulatory exposure under FCCPA 2018 | Medium | §7 decision required before Phase 1 pricing engine is finalised |
| Frontend keeps calculating prices in parallel | Silent totals mismatch, disputed charges | High | Server response carries display strings; CI grep bans arithmetic on price fields in components |
| Webhook endpoint unreachable or unverified | Paid orders never confirmed, or fraudulent free orders | Medium | Signature verification, idempotency, plus a scheduled reconciliation job that re-verifies pending payments |
| The three duplicate component families drift further during integration | Bugs fixed in one path, live in another | High | Delete duplicates before integration, not after |
| Reservations go live without capacity modelling | Double-booked tables, angry customers | Medium | RES-6 database-level constraint; no launch without it |
| Scope creep from Phase 3 into Phase 1 | Nothing ships | High | This document; phase gates in `ROADMAP.md` |

---

## 11. Document map

| Document | Contents |
|---|---|
| [`docs/FRONTEND_AUDIT.md`](docs/FRONTEND_AUDIT.md) | Evidence-based teardown of the existing frontend |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Django project layout, apps, request lifecycle, conventions |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Every model, field, constraint and index |
| [`docs/API_SPEC.md`](docs/API_SPEC.md) | Every endpoint with request/response shapes |
| [`docs/AUTH.md`](docs/AUTH.md) | allauth configuration, session/CSRF/CORS across origins |
| [`docs/PAYMENTS.md`](docs/PAYMENTS.md) | Paystack/Flutterwave flows, webhooks, money handling rules |
| [`docs/ORDERS_AND_FULFILMENT.md`](docs/ORDERS_AND_FULFILMENT.md) | Order state machine, KDS, delivery zones, riders |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat model, PCI posture, NDPR, hardening checklist |
| [`docs/FRONTEND_INTEGRATION.md`](docs/FRONTEND_INTEGRATION.md) | File-by-file changes required in `frontend/` |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phased delivery plan with gates |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Environments, env vars, infrastructure options |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy and the non-negotiable money tests |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Architecture decision records |
