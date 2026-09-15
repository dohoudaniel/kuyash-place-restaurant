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

### 1E — Payments (1 week) — ✅ IMPLEMENTED
Provider interface · Paystack · Flutterwave · initialise/verify · **webhook handlers with signature verification and idempotency** · reconciliation beat task · refunds · cash and transfer flows.

Delivered: the `payments` app with a provider protocol and three
implementations (Paystack, Flutterwave, plus a simulator usable only under
DEBUG), signature-verified webhooks, the amount-mismatch guard, reconciliation
and expiry beat tasks, full and partial refunds, and bank-transfer and cash
flows. **100% coverage on `payments.services` and `payments.tasks`**, now in
the same CI gate as money, pricing and orders.

Verified end to end: a forged signature is rejected with the order left unpaid;
an underpayment of ₦10 against a ₦21,800 order is refused and logged CRITICAL
with the order still unpaid; the correct amount settles; a replay is recognised
and ignored. No PAN or CVV column exists on any model.

Notes:

- **Two functions are deliberately not atomic.** `initialise_payment` and
  `verify_and_settle` each write a failure record and then raise. Wrapping
  either in a transaction rolled that record back with the exception,
  destroying the evidence of an outage, a bad key or a suspicious payment.
  Only `_settle` is atomic, because the transaction and the order status must
  move together.
- **Provider JSON is parsed with `parse_float=Decimal`.** Flutterwave reports
  major units (`25500.55`), and `json.loads` would make that a binary float
  before we ever saw it.
- **A missing provider key is an error in production, not a downgrade.**
  `prod.py` refuses to start without one, and the simulator is reachable only
  under DEBUG — a provider that approves everything must never be a fallback.
- **The PCI gate is now split.** Backend coverage is an AST check in the test
  suite; the shell script covers the frontend only. A text scan could not tell
  a real field from a docstring saying "there is no CVV field here".

### 1F — Notifications & hardening (0.5 week) — ✅ IMPLEMENTED
Email templates and outbox · order lifecycle emails · security checklist · load test at 200 concurrent orders.

Delivered: ten admin-editable `EmailTemplate` rows with built-in fallbacks,
multipart (text + HTML) sending, the full order lifecycle wired to templates,
six `kuyash.*` deployment checks derived from `SECURITY.md` §8, a Locust load
profile, and concurrency-correctness tests.

**The fallback rule:** a missing, inactive or malformed template degrades the
*wording*, never the delivery. A customer who paid and hears nothing is a
support call; slightly off-brand prose is not.

Notes:

- **Throughput was not measured here.** The load profile is written and ready,
  but running it against the SQLite development database would measure
  SQLite's write lock rather than the application. It needs a Postgres staging
  environment; the targets remain as stated in `TESTING.md` §10.
- **Correctness under concurrency *is* asserted**, in
  `apps/orders/tests/test_concurrency.py`. Two of those tests need real row
  locking and are skipped on SQLite — so CI now runs the whole suite a second
  time against Postgres and **fails if they are still skipped there**, because
  a skip nobody checks is just a hole.
- `manage.py check --deploy` now passes cleanly on a well-formed production
  configuration and reports specifically on a malformed one.

### Gate 1 — go-live checklist

> **All Phase 1 code is implemented.** Everything outstanding below is a
> decision, a data entry task, or a frontend deletion — not backend work.

- [x] All eleven success criteria in `PRD.md` §9 demonstrated end-to-end — criteria 1–10 as one customer-and-kitchen journey through the API (`orders/tests/test_prd_success_criteria.py`: register → verify → staff-set menu → priced modifiers on a cart that follows the customer across devices → server totals that ignore tampering → promo validated, usage-limited and un-enumerable → hosted checkout with no card data stored → KDS push and ticket within 15 s → advanced to delivered, each status visible on `/orders/{ref}`, confirmation and dispatch emails → server-backed history); criterion 11 by the CI gate `scripts/check-no-alert.sh`. Re-run on staging with real Paystack test keys before launch
- [ ] **Zero menu items with `needs_repricing=True`** — the owner has set real naira prices
- [ ] Tax policy (`PRD.md` §7) decided; `/help` and `/terms` copy corrected
- [x] Card fields deleted from the frontend; CI gate passing — allowlist now empty
- [ ] Security checklist (`SECURITY.md` §8) fully ticked
- [x] 100% coverage on money, tax, discount, payment and state-machine logic — enforced in CI: `apps.common.money`, and the money path (`carts`, `promotions`, `orders` and `payments` services, payment tasks and provider adapters, `loyalty.services`, `academy.services`) with `--cov-fail-under=100`
- [x] Webhook forgery, amount-mismatch and replay tests passing — `payments/tests/test_webhooks.py`, `test_webhook_edges.py`, `test_payment_flows.py` (see `SECURITY.md` §8)
- [ ] Backup restore actually performed on a staging database — run `scripts/restore-drill.sh` (see `DEPLOYMENT.md` §8.2) and record the date there; the scripts and `verify_restore` are built and exercised in CI
- [ ] Staff trained on the KDS; a dry-run service completed
- [ ] Phase 2/3 features hidden or marked "coming soon" — **not faked**

---

## Phase 2 — Service operations (~3–4 weeks)

| # | Feature | Est. | Status |
|---|---|---|---|
| 2.1 | Reservations: tables, areas, service periods, **exclusion-constraint availability**, confirmation emails, admin book view | 1.5 wk | ✅ |
| 2.2 | Catering: packages, enquiries, staff workflow, indicative totals, overdue-response view | 0.5 wk | ✅ |
| 2.3 | Support: contact → tickets, replies, FAQ admin, spam protection | 0.5 wk | ✅ |
| 2.4 | Wishlist sync + saved payment methods (provider tokens) | 0.5 wk | ✅ |
| 2.5 | Social login (Google, Facebook) | 0.3 wk | ✅ |
| 2.6 | CMS: legal pages with versioning, opening-hours editing, site settings | 0.5 wk | ✅ |
| 2.7 | Reorder with revalidation; PDF receipts | 0.3 wk | ✅ |

#### 2.1 delivered

`reservations` app: TableArea, RestaurantTable, ServicePeriod, BlackoutDate and
Reservation; a computed availability engine; booking, rescheduling and
cancellation with guest emails; a staff day-book endpoint. 70 tests.

The double-booking guarantee has two layers: a row lock during table allocation,
and — on Postgres — an `ExclusionConstraint` over `(table, [start, end))` added
by migration `0002_no_double_booking`. SQLite has no equivalent (ADR-015), so
the concurrency proof is skipped there and **CI now fails if any
Postgres-gated test is still skipped on the Postgres job**.

Demonstrated end to end: two private-room tables book, the third party is
refused, a 120-minute turn at 19:00 correctly blocks 20:00, cancelling frees
the table, every guest is emailed, and the database holds zero double-booked
tables.

#### 2.2 delivered

`catering` app: packages, enquiries, an indicative total computed server-side,
and an **SLA clock** measured against the 24-hour callback the website already
promises. 27 tests.

Three things happen on submission, where the current form does none of them:
the enquiry is persisted with a reference, the customer is acknowledged with a
concrete deadline, and the team is emailed. Overdue enquiries surface both in
the admin changelist (as a red banner) and at
`GET /catering/enquiries/overdue/` for managers.

Demonstrated: a 300-guest wedding enquiry worth an indicative ₦3.6M is
recorded, both parties are emailed, it goes 12 hours overdue and appears in the
manager's queue, then answering it clears the queue. Internal notes and the
real quote are never exposed to the customer.

#### 2.3 delivered

`support` app: contact messages, tickets with threaded replies, an editable
FAQ, and spam protection. 30 tests.

A contact submission now persists, opens a ticket, acknowledges the customer
and alerts the team. Spam is **quarantined, not rejected** — a bot gets exactly
the same response shape and status code as a real customer, so it learns
nothing. Internal notes are never emailed or returned by the API.

The seeded FAQ corrects the tax contradiction: `app/help/page.tsx` claims
prices include tax while the cart adds 7.5% on top. The seeded answer is
generated from `Branch.prices_include_vat`, so it cannot disagree with what the
system actually charges. That said, **OD-1 is still open** — the decision itself
has not been made, only made consistent.

#### 2.4 delivered

`WishlistItem` (in `catalog`, so the dependency runs the right way) and
`SavedPaymentMethod` (in `payments`). 31 tests, 100% coverage on both view
modules.

**Wishlist** — server-side, so a saved dish survives a new device, a cleared
browser and a private window, none of which `localStorage` does. `POST
/wishlist/sync/` folds a browser's list into the account on first sign-in;
it is **additive**, so signing in never loses something saved on either side,
and unmatched slugs are reported rather than dropped — the frontend's list is
keyed on an image filename (`signatureGrillPlate`) and will contain stale
entries.

**Saved cards** — a provider token and a last-four, never a card. Two decisions
worth recording:

- **A card is saved only if the customer asked.** A provider returns a reusable
  token whether or not anyone wanted the card kept; persisting one regardless
  would be collecting a payment credential without consent. `save_card` on
  initialise sets `PaymentTransaction.save_method`, and only then does
  settlement store a token.
- **Forgetting a card deactivates it.** A hard delete would orphan the token's
  trail on historical transactions.

Found while building: a serializer field named `label` shadows DRF's
`Field.label`. Exposed as `card_label` instead.

#### 2.5 delivered

Google and Facebook sign-in through allauth, replacing
`alert("Google login - Integration needed")`. 13 tests, 100% coverage on the
adapters.

The security question this had to settle: **can social sign-in take over
someone else's account?** It cannot. The two providers are configured
differently on purpose:

- **Google** asserts `email_verified`, so it auto-links to an existing
  password account. Without that, a customer who registered with a password and
  later clicks "Continue with Google" hits a confusing duplicate-email error.
- **Facebook** does not verify reliably, so it does **not** auto-link. A
  `pre_social_login` check refuses the link and returns 409
  `social_email_unverified`. The attack it blocks: create an account at a
  provider that does not verify addresses, assert the victim's email, and be
  signed in as them.

Also: provider access tokens are not stored (`SOCIALACCOUNT_STORE_TOKENS =
False`) — we never act on the customer's behalf, so keeping one would be
holding a credential with no purpose. Auto-signup requires an email, since
without one there is nothing to send an order confirmation to.

#### 2.6 delivered

Legal pages as data, versioned. `GET /core/legal/` and `GET /core/legal/{slug}/`
replace five hardcoded route files; the admin holds the history. 36 tests, 100%
coverage on the model, views, checks, seed and admin.

Two decisions worth stating, because both are the kind of thing that quietly
rots otherwise.

**A published version is read-only.** Which wording a customer agreed to matters
if it is ever disputed, and a page that staff can edit in place means that
record is whatever the last person to touch it decided it was. Changing the text
drafts a new version (`(slug, version)` is unique); the old one stays readable
and `LegalPage.current()` picks the one in force today. Drafts and future-dated
versions return 404 rather than leaking wording that does not yet apply. The
`published` flag stays editable so a bad page can still be pulled.

**The tax-copy contradiction is now a build failure.** `app/terms/page.tsx:47`
and `app/help/page.tsx:120` promised "prices … include applicable taxes" while
`CartSummary.tsx:23` added 7.5% on top — a misleading price representation under
the FCCPA 2018, and one that survived because the copy and the arithmetic lived
in different files owned by different people. Two things now prevent it:

- The pricing sentence in the seeded terms is **generated** from
  `Branch.prices_include_vat`, so the seeded copy cannot disagree with the cart.
- `manage.py check --deploy` fails with **`kuyash.E002`** when any published page
  asserts a VAT direction the branch does not charge. It looks for the
  *opposing* claim rather than for exact seeded wording — staff can reword these
  pages freely, and only a contradiction fails the build. A check that fired on
  every legitimate edit would be switched off within a week.

`kuyash.W003` additionally warns when `terms`, `privacy` or `refunds` has no
published version, because a footer link that 404s is worse than no link.

This does **not** close OD-1. Whichever direction the owner picks, the published
pages and the cart now have to agree — that is all the gate enforces.

---

#### 2.7 delivered

Reorder and PDF receipts. 40 tests, 100% coverage on
`apps/orders/services/reorder.py`, `services/receipt.py` and `reorder_views.py`.

**Reorder is a fresh quote, not a copy.** `OrderHistorySection.tsx` pushes the
stored line objects straight back into the cart store — the old prices, dishes
that may have left the menu, options that may no longer exist. Every line is now
re-resolved against the current catalogue: it comes back at today's price with
any difference reported, and a delisted dish, a withdrawn size or a required
option with nothing left to choose is skipped and named rather than substituted.
The repricing gate applies here too, so an unpriced item cannot re-enter a
basket through order history.

It also refuses to overwrite a basket that already has lines (`409
cart_not_empty`) unless the caller confirms. Silently discarding what the
customer had already chosen, to save them a tap, is not a convenience.

**Receipts are refused for unpaid orders** (`409 order_not_paid`). A document
headed "Receipt" for money that was never received causes the dispute it is
meant to settle.

One trap worth recording: **the naira sign does not survive a PDF.** The
standard PDF fonts use WinAnsiEncoding, which has no U+20A6, and reportlab
substitutes it without warning — `₦33,120.00` prints as `n33,120.00`. Receipts
use `format_money_ascii` (`NGN 33,120.00`) and a test asserts the symbol never
appears in the rendered bytes. The JSON API is unchanged.

Receipts print the VAT rate and direction snapshotted on the order, never
today's branch settings; a receipt already issued must not change because the
restaurant later changed its pricing.

---

**Gate 2:** a reservation cannot be double-booked (proven by a concurrency test); every catering enquiry reaches a human with an SLA timer; no form anywhere in the app still `alert()`s.

Status: the first two are **met and demonstrated**. The third is met on the
backend for every Phase 2 form (contact, catering, reservations) — reviews and
academy enrolment are Phase 3, and the frontend still has to be wired to these
endpoints (`docs/FRONTEND_INTEGRATION.md`).

**Phase 2 is code-complete**: 2.1 through 2.7 all delivered, 866 tests passing,
97% coverage overall and 100% on every money, pricing, order-state, payment,
reorder and receipt path. What remains before Gate 2 can be signed off is not
backend work:

1. The frontend has to actually call these endpoints. Nothing in `frontend/`
   makes a network request yet — that is `docs/FRONTEND_INTEGRATION.md`.
2. ~~The card fields have to be deleted~~ — **done** in frontend integration
   step 2. `KNOWN_FRONTEND_DEBT` in `scripts/check-no-card-fields.sh` is empty.
3. The owner decisions in `DECISIONS.md` (OD-1 through OD-6) still block Gate 1,
   and Gate 1 comes first. `manage.py check --deploy` fails today with
   `kuyash.E001` for 18 unpriced items, by design.

---

## Phase 3 — Growth (~4–5 weeks)

| # | Feature | Est. |
|---|---|---|
| 3.1 | ✅ Reviews: verified purchase, moderation queue, aggregate recalculation | 0.7 wk |
| 3.2 | ✅ Academy: instructors, courses, cohorts, enrolments, payments, certificates | 1.5 wk |
| 3.3 | ✅ Loyalty: ledger, tiers, rewards, redemption, refund reversal | 1 wk |
| 3.4 | ✅ Gallery CMS | 0.3 wk |
| 3.5 | ✅ Chat: FAQ matching, order lookup, ticket escalation | 0.7 wk |
| 3.6 | ✅ Django Channels: live KDS and order tracking over WebSockets | 0.7 wk |
| 3.7 | ✅ Reporting: sales, popular items, peak hours, rider performance | 0.5 wk |

**Gate 3:** every screen in the frontend is backed by real data. No mock arrays remain anywhere in `frontend/`.

> **Status:** the frontend side is met. Help reads the FAQ API; the five policy pages render the versioned legal pages; homepage stats, hero hours, footer social links and the About page read site settings, team and awards; the dead chat widget copy and `lib/data/hero.ts` are deleted. What remains is owner content — OD-2 (prices, photos), OD-9 (rewards terms) and OD-10 (About copy and figures) — plus 3.6 and 3.7.

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
