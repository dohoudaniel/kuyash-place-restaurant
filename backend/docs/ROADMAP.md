# Roadmap

Three phases with hard gates. A phase does not start until the previous phase's gate is signed off.

Estimates assume **one full-time backend developer**. Adjust proportionally.

---

## Phase 0 — Foundations (~1 week)

| # | Task |
|---|---|
| 0.1 | Django project scaffold, split settings, `django-environ` |
| 0.2 | Dependency-free local dev: SQLite, in-memory cache, eager Celery (ADR-015). No Docker. |
| 0.3 | `apps/common`: `TimeStampedModel`, `MoneyField`, `Money` value object, VAT maths |
| 0.4 | DRF + `drf-spectacular` + problem-details exception handler |
| 0.5 | Custom `User` (email login) + allauth wiring |
| 0.6 | `core`: Branch, OpeningHours, SiteSettings + seed |
| 0.7 | Celery + beat; email backend via the `notifications` outbox |
| 0.8 | Supabase Storage via `django-storages` |
| 0.9 | CI: ruff, mypy, pytest, `check --deploy`, gitleaks, **the card-field grep gate** |
| 0.10 | Sentry + structured JSON logging |

**Gate 0:** `make install migrate seed run` gives a working Django with OpenAPI docs, a seeded branch, a passing CI pipeline, and a money module with 100% test coverage — with no database or queue daemon installed.

---

## Phase 1 — Ordering core (~5–7 weeks)

The phase that makes the product real.

### 1A — Catalogue (1 week) — ✅ IMPLEMENTED
Categories, MenuItem, Variant, ModifierGroup, Modifier, DietaryTag, images, availability windows · admin with the **repricing banner** · public read API with server-side search/filter/sort · seed the 18 items with `needs_repricing=True`.

Delivered: 8 models, 5 public endpoints, the `kuyash.E001` deploy gate, 41 tests.
All five sort options work server-side (the frontend's `rating` and `newest` are
`return 0`). Breakfast items carry real availability windows. Modifier groups are
per item, so pancakes are no longer offered extra cheese.

> Note: the menu list uses **page** pagination, not cursor. Cursor pagination
> imposes its own ordering to keep the cursor monotonic, which silently
> overrode every `sort` parameter. See `docs/API_SPEC.md` §0.3.

### 1B — Accounts (1 week) — ✅ IMPLEMENTED
Registration with mandatory verification · login/logout/session · password reset · profile · address book with zone resolution · guest-order claiming · rate limits · Argon2.

Delivered: 14 auth/account endpoints, `Address` with automatic zone resolution,
a `delivery.DeliveryZone` model (riders remain in 1D), a recorded notifications
outbox, per-IP **and** per-account throttling, and NDPR erasure by anonymisation.
101 tests.

Deviations, all deliberate:

- **`delivery` landed early.** The address book needs zones to resolve a fee, so
  `DeliveryZone` was built here. `RiderProfile` / `DeliveryAssignment` stay in 1D.
- **A minimal `notifications` outbox landed early** (scheduled for 1F). Auth
  sends two emails and NOT-3 requires every send to be recorded; retrofitting
  that later would have meant rewriting the send path.
- **Guest-order claiming is a signal, not an implementation.** `Order` does not
  exist yet. `accounts.signals.email_verified` fires on confirmation; `orders`
  connects to it in 1D, so `orders` is never imported by `accounts` (ADR-014).
- **Email change is refused, not implemented.** AS-5 requires re-verifying a new
  address and notifying the old one. Until that flow exists, `email` is
  read-only on the profile endpoint — you cannot bypass verification for a change
  that cannot be made. A dedicated flow lands in Phase 2.

### 1C — Cart & pricing (1 week) — ✅ IMPLEMENTED
Server cart, guest tokens, merge-on-login · **the pricing engine** (per-line VAT by tax class, promo application, delivery fee, tip) · repricing on read with `changes[]`/`unavailable[]` · promo codes with the redemption ledger.

> This is the highest-risk sub-phase. Budget the full week for tests.

Delivered: `carts` and `promotions` apps, 9 cart endpoints, **100% coverage on
every module that can change what a customer is charged** (`carts.services`,
`promotions.services`) — now enforced as its own CI gate alongside the money
module. 116 tests across the two apps.

The pricing engine reproduces the worked example in `PAYMENTS.md` §7.1 exactly,
asserted as a test: if the engine and the documentation ever disagree, the build
fails.

Deviations:

- **`PromoRedemption` has no `order` foreign key yet.** `Order` does not exist
  until 1D, so the ledger references an order by its opaque `order_reference`
  string. 1D replaces that with a proper FK. Usage limits are already enforced
  and reversible against the ledger.
- **Seeded promo codes are INACTIVE.** The five codes in
  `frontend/lib/store/promoStore.ts` are dollar figures ("₦5 off orders over
  ₦30"), and `SAVE500` has `value: 5` — its name and value already disagree.
  They are seeded converted to plausible naira but disabled, so none can be
  redeemed before a human reviews it. This is the promo equivalent of the
  `needs_repricing` gate.
- **Menu list pagination is page-based, not cursor.** Recorded in §0.3 of
  `API_SPEC.md` when it was found.

### 1D — Orders & KDS (1.5 weeks) — ✅ IMPLEMENTED
Order + OrderItem snapshots · reference generation · idempotency middleware · the state machine and event log · ETA calculation · order APIs with ETag polling · KDS endpoints · "86 this item" · delivery zones and rider assignment.

Delivered: the `orders` app (Order, OrderItem, OrderItemModifier,
OrderStatusEvent), 4 customer endpoints and 5 KDS endpoints, rider profiles and
delivery assignments. **100% coverage on `orders.services`**, now part of the
same CI gate as money and pricing — the state machine governs refunds.

Verified end to end: a double-tapped submit with one `Idempotency-Key` produces
one order and replays the first response; the cart is cleared only when payment
is verified, not at submit; `If-None-Match` returns 304 on an unchanged order.

Notes:

- **Cash orders skip `accept`.** They are created `confirmed`, so the kitchen's
  accept step does not apply — attempting it correctly returns 409.
- **The customer cancel window is enforced at the endpoint, not the state
  table.** The table lets staff cancel a preparing order; a customer may not
  (ORD-10). The transition table alone cannot express "who is asking".
- **Payment is still simulated.** `transition(order, PAID)` stands in for the
  verified webhook that Phase 1E adds. No money moves yet.

### 1E — Payments (1 week)
Provider interface · Paystack · Flutterwave · initialise/verify · **webhook handlers with signature verification and idempotency** · reconciliation beat task · refunds · cash and transfer flows.

### 1F — Notifications & hardening (0.5 week)
Email templates and outbox · order lifecycle emails · security checklist · load test at 200 concurrent orders.

### Gate 1 — go-live checklist

- [ ] All eleven success criteria in `PRD.md` §9 demonstrated end-to-end
- [ ] **Zero menu items with `needs_repricing=True`** — the owner has set real naira prices
- [ ] Tax policy (`PRD.md` §7) decided; `/help` and `/terms` copy corrected
- [ ] Card fields deleted from the frontend; CI gate passing
- [ ] Security checklist (`SECURITY.md` §8) fully ticked
- [ ] 100% coverage on money, tax, discount, payment and state-machine logic
- [ ] Webhook forgery, amount-mismatch and replay tests passing
- [ ] Backup restore actually performed on a staging database
- [ ] Staff trained on the KDS; a dry-run service completed
- [ ] Phase 2/3 features hidden or marked "coming soon" — **not faked**

---

## Phase 2 — Service operations (~3–4 weeks)

| # | Feature | Est. |
|---|---|---|
| 2.1 | Reservations: tables, areas, service periods, **exclusion-constraint availability**, confirmation emails, admin book view | 1.5 wk |
| 2.2 | Catering: packages, enquiries, staff workflow, indicative totals, overdue-response view | 0.5 wk |
| 2.3 | Support: contact → tickets, replies, FAQ admin, spam protection | 0.5 wk |
| 2.4 | Wishlist sync + saved payment methods (provider tokens) | 0.5 wk |
| 2.5 | Social login (Google, Facebook) | 0.3 wk |
| 2.6 | CMS: legal pages with versioning, opening-hours editing, site settings | 0.5 wk |
| 2.7 | Reorder with revalidation; PDF receipts | 0.3 wk |

**Gate 2:** a reservation cannot be double-booked (proven by a concurrency test); every catering enquiry reaches a human with an SLA timer; no form anywhere in the app still `alert()`s.

---

## Phase 3 — Growth (~4–5 weeks)

| # | Feature | Est. |
|---|---|---|
| 3.1 | Reviews: verified purchase, moderation queue, aggregate recalculation | 0.7 wk |
| 3.2 | Academy: instructors, courses, cohorts, enrolments, payments, certificates | 1.5 wk |
| 3.3 | Loyalty: ledger, tiers, rewards, redemption, refund reversal | 1 wk |
| 3.4 | Gallery CMS | 0.3 wk |
| 3.5 | Chat: FAQ matching, order lookup, ticket escalation | 0.7 wk |
| 3.6 | Django Channels: live KDS and order tracking over WebSockets | 0.7 wk |
| 3.7 | Reporting: sales, popular items, peak hours, rider performance | 0.5 wk |

**Gate 3:** every screen in the frontend is backed by real data. No mock arrays remain anywhere in `frontend/`.

---

## Deferred (explicitly not scheduled)

Loyalty points expiry automation · scheduled/pre-orders · gift cards · multi-branch activation · PostGIS polygon zones · virtual accounts for transfer reconciliation · SMS/WhatsApp · native apps · POS integration · inventory depletion · AI chat.

---

## Critical path

```
Phase 0 ──▶ 1A catalogue ──▶ 1C cart/pricing ──▶ 1D orders ──▶ 1E payments ──▶ GATE 1
              │                    ▲
              └─▶ 1B accounts ─────┘
```

**1C (pricing) is the bottleneck.** Nothing downstream can be trusted until it is exhaustively tested. Do not compress it.

---

## Parallelisation with a second developer

| Dev A (backend core) | Dev B (frontend integration) |
|---|---|
| Phase 0 | Delete dead trees; delete card fields; build the API client |
| 1A catalogue | Auth UI rewrite against a mocked API |
| 1C cart/pricing | Menu integration against 1A |
| 1D orders + KDS | Cart integration against 1C |
| 1E payments | Checkout + order tracking |

Dev B is unblocked from day one by the OpenAPI schema, which exists from Phase 0.

---

## Risks to the schedule

| Risk | Mitigation |
|---|---|
| Repricing never happens, blocking Gate 1 | Chase the owner for prices during Phase 0, not Phase 1 |
| Tax policy undecided | `PRD.md` §7 needs an answer before 1C |
| Frontend debt slows every integration PR | Do the deletions in Phase 0/1A, before integration starts |
| Payment provider onboarding delays (business verification) | Start Paystack/Flutterwave account setup in Phase 0 |
| Scope creep from Phase 3 | Phase gates; features hidden, never half-built |
