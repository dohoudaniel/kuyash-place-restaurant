# Architecture Decision Records

Decisions taken for the Kuyash Place backend, with the reasoning preserved so they can be revisited deliberately rather than accidentally.

---

## ADR-001 — Phased build, with unbuilt features hidden rather than faked

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** The frontend presents ~25 features; roughly 70% are simulated with `alert()`. Building all of them before anything ships would take months with no revenue.

**Decision.** Three phases. Phase 1 is the ordering core. Features not yet built are **hidden or explicitly marked "coming soon"** in the UI.

**Consequences.** Revenue starts at the end of Phase 1. The "coming soon" rule is the important half: a reservation form that silently discards a booking is worse than no form, because the customer believes they have a table.

---

## ADR-002 — Paystack primary, Flutterwave secondary, both hosted checkout

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** Nigerian market, naira only. The frontend currently collects raw PAN and CVV in React state.

**Decision.** Hosted/inline provider checkout, Paystack default with Flutterwave fallback, behind a single `PaymentProvider` interface. **The existing card form is deleted, not connected.**

**Consequences.** PCI-DSS scope stays at SAQ A (~30 controls) instead of SAQ D (~300). Card data never touches our infrastructure. We give up full control of the payment UI — an acceptable trade for eliminating the single largest liability in the codebase. A CI grep gate prevents regression.

**Rejected:** direct card processing (compliance cost); a single provider (no failover in a market where outages happen).

---

## ADR-003 — Session cookies via django-allauth, not JWT in localStorage

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** Browser-only product handling money. No existing auth to migrate.

**Decision.** HttpOnly, Secure, SameSite=Lax session cookies on a shared parent domain. allauth handles registration, verification, reset and (Phase 2) social login.

**Consequences.** A token cannot be stolen by XSS. Revocation is immediate. Requires CSRF handling and a shared parent domain — an infrastructure constraint documented in `DEPLOYMENT.md` §2.1. A future mobile app gets a separate token-auth path.

---

## ADR-004 — Polling before WebSockets

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** Order tracking and the KDS both want live updates. Channels needs ASGI plus a Redis channel layer.

**Decision.** Poll `GET /orders/{ref}/` every 15s with `ETag`/`If-None-Match`. KDS polls every 10s. Channels deferred to Phase 3.

**Consequences.** No ASGI or channel-layer complexity on day one. At the expected volume (< 200 concurrent orders) a 304-returning poll is cheap. Up to 15s of latency — acceptable for food, not for a stock ticker. The API shape does not change when WebSockets arrive; only the transport does.

---

## ADR-005 — Money as integer kobo, never float or Decimal-in-the-DB

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** The frontend stores prices as strings (`"₦14.90"`), parses them with a regex into floats, and does float arithmetic for VAT, discounts and totals.

**Decision.** All money is `PositiveBigIntegerField` holding kobo. `Decimal` only for intermediate ratio maths, rounded to integer immediately with `ROUND_HALF_UP`. `float` is banned in every money path and enforced by a static check. The API returns `{amount, currency, display}` so the frontend never formats currency.

**Consequences.** No floating-point drift, ever. Slightly more verbose code. Developers must internalise that `1000` means ₦10.00 — mitigated by `MoneyField.help_text` and factories that always use explicit kobo.

---

## ADR-006 — Django admin plus a purpose-built KDS

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** Staff need to manage content *and* run service. These are different jobs with different tempos.

**Decision.** Customised Django admin for menu, pricing, promos, refunds and reports. A separate, minimal KDS endpoint set and screen for live order handling.

**Consequences.** Admin is free and powerful for content. The KDS is small (one list, four buttons) and tuned for a kitchen during a rush, where stock admin would be dangerous — a misclick on a changelist should not cancel an order. A full staff dashboard in Next.js was rejected as disproportionate for one location.

---

## ADR-007 — Own riders with zone-based flat delivery fees

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** The frontend hardcodes a flat ₦5.00 delivery fee (a dollar figure). Lagos addressing makes distance calculation unreliable.

**Decision.** Named zones, each with a flat fee, minimum order value and ETA. Phase 1 resolves a zone by string matching with a manual override; Phase 3 may add PostGIS polygons.

**Consequences.** Predictable for customers, simple to operate, no Maps API billing. Zone edges are approximate — the manual override handles disputes. Third-party logistics was rejected as an unnecessary dependency and per-order cost for a single location.

---

## ADR-008 — The backend owns prices; seeds are flagged `needs_repricing`

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** Menu prices in `lib/data/menu.ts` are dollar amounts wearing a ₦ sign — ₦14.90 for a grill plate, ₦10.90 for a burger, ₦5.00 delivery, ₦2/₦5/₦10 tips. Catering (₦3,500–₦12,000/head) and academy (₦40,000–₦75,000) are plausible naira. Two currencies, one symbol.

**Decision.** Prices move to the database as kobo. Every seeded menu price carries `needs_repricing=True`. Such items are **excluded from the public API**, the admin shows a blocking banner, and `manage.py check --deploy` **fails** while any active item is unconfirmed.

**Consequences.** Launching with ₦14.90 burgers becomes structurally impossible rather than a thing someone must remember. The owner must do real pricing work before Gate 1 — which is correct, and is on the critical path.

---

## ADR-009 — Single branch, modelled for multiple

**Date:** 2026-09-11 · **Status:** Accepted

**Decision.** A `Branch` table with exactly one row. Menus, prices, hours, zones, stock and orders all FK to it.

**Consequences.** Small cost now: one extra FK and a `get_current_branch()` helper. Avoids the migration that retrofitting a branch onto a live orders table would require. Multi-branch *activation* (customer branch selection, routing) is deferred and unscheduled.

---

## ADR-010 — Supabase Storage for media

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** Media currently lives in `public/images/` and is indexed by a hand-maintained `IMAGES` registry in `lib/assets/images.ts`. Several menu entries and **all 20 gallery entries** reference keys with no corresponding file.

**Decision.** Supabase Storage via `django-storages`' S3 backend (path-style addressing, public read). A Celery task generates `thumb`/`card`/`full` derivatives.

**Consequences.** Staff upload dish photos from a phone through the admin. `lib/assets/images.ts` is deleted, and with it the class of bug where a key and a file disagree. Requires `next.config.ts` `remotePatterns` — currently an empty config, so this is a hard prerequisite.

---

## ADR-011 — Transactional email only; SMS and WhatsApp deferred

**Date:** 2026-09-11 · **Status:** Accepted

**Decision.** Email is the only outbound channel in Phase 1–2, sent asynchronously through a recorded outbox.

**Consequences.** Zero per-message cost, no provider onboarding, and allauth needs email regardless. SMS has better reach in Nigeria and is the most likely first addition — the `Notification.channel` field already anticipates it, so adding it is additive.

---

## ADR-012 — Scripted FAQ chat bot with ticket handoff, not AI

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** The chat widget currently echoes locally. A restaurant bot that invents a delivery fee or a price creates a real obligation.

**Decision.** Keyword matching against admin-managed `FaqEntry` rows, plus an order-status lookup by reference. Anything unmatched becomes a support ticket.

**Consequences.** The bot cannot fabricate prices or delivery promises, because it can only return stored answers. No per-message cost, no guardrail engineering. Less impressive than an LLM — revisit once there is enough ticket volume to know what people actually ask.

---

## ADR-013 — Services layer, not fat models

**Date:** 2026-09-11 · **Status:** Accepted

**Context.** Pricing spans catalogue, cart, promotions, delivery and branch tax policy simultaneously. No single model can own it without importing its siblings.

**Decision.** Business logic lives in `services.py` as functions over loaded data. Views do authz, deserialise, call a service, serialise. Models hold persistence and per-row invariants.

**Consequences.** The pricing engine is unit-testable without HTTP or, largely, the database — which is what makes the 100% coverage requirement achievable rather than aspirational. Slightly more files per app.

---

## ADR-014 — Domain signals for cross-app reactions

**Date:** 2026-09-11 · **Status:** Accepted

**Decision.** `orders` emits `order_status_changed`; `loyalty`, `notifications`, `reviews` and `catalog` subscribe. `orders` never imports them.

**Consequences.** Phase 3 apps land without touching Phase 1 code — the property that makes the phased plan actually work. Trade-off: the flow is less traceable by reading alone, so every signal and its receivers are listed in `ARCHITECTURE.md` §6.3.

---

## ADR-015 — No Docker for local development

**Date:** 2026-09-11 · **Status:** Accepted · **Supersedes part of ADR-nil (Phase 0 plan)**

**Context.** The original Phase 0 plan assumed `docker compose up` for Postgres and Redis. The team does not use Docker locally.

**Decision.** Local development runs on a plain virtualenv with **zero external services**:

- **Database** — SQLite by default. `DATABASE_URL` switches to Postgres when one is available.
- **Cache** — in-memory `LocMemCache` when `REDIS_URL` is unset.
- **Celery** — `CELERY_TASK_ALWAYS_EAGER` defaults to `True` when `REDIS_URL` is unset, so tasks run synchronously in-process.
- **Email** — console backend.
- **Media** — local disk until `SUPABASE_S3_ENDPOINT` is set.

Staging and production still require Postgres and Redis; `config/settings/prod.py` raises at import if `REDIS_URL` is missing.

**Consequences.** `make venv install migrate seed run` gets a working API with no daemons to install — the fastest possible path to a running system, which matters most in the phase where nothing works yet.

The cost is a dev/prod database divergence. It is bounded and managed:

- `settings.USING_POSTGRES` guards Postgres-only features.
- Postgres-only constructs arrive in Phase 1A (GIN search) and Phase 2 (`ExclusionConstraint` for reservation double-booking). **Those must be developed and tested against Postgres**, not SQLite — set `DATABASE_URL` locally or rely on CI.
- CI runs the suite against **both** SQLite (fast) and Postgres (truthful) from Phase 1A onward, so divergence is caught by the build rather than by a customer.

**Rejected:** requiring a locally installed Postgres (setup friction for a one-developer project); SQLite everywhere including production (no concurrency, no exclusion constraints, no PITR).

---

## Open decisions

| # | Question | Needed by | Owner |
|---|---|---|---|
| **OD-1** | **VAT-inclusive or VAT-exclusive pricing?** (`PRD.md` §7) | Before Phase 1C | Product owner |
| OD-2 | Real naira prices for the 18 menu items | Before Gate 1 | Product owner |
| OD-3 | Real delivery zones, fees and minimums | Before Gate 1 | Product owner |
| OD-4 | Deployment target (`DEPLOYMENT.md`) | Before Gate 1 | Engineering |
| OD-5 | Keep or remove the academy "installment" option (ACA-6) | Phase 3 | Product owner |
| OD-6 | Tip presets — the current ₦2/₦5/₦10 are dollar figures | Before Gate 1 | Product owner |
