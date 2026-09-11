# Kuyash Place Restaurant — Backend

Django backend for Kuyash Place Restaurant: ordering, payments, reservations, catering, academy and loyalty for a single-location Nigerian restaurant.

**Status:** Phase 0 (foundations) implemented. Phase 1 not started.
**Stack:** Django 5.x · DRF · PostgreSQL 16 · Redis 7 · Celery · django-allauth · Supabase Storage

---

## Start here

**If you read one thing:** [`docs/FRONTEND_AUDIT.md`](docs/FRONTEND_AUDIT.md).

The `frontend/` application is a 16,432-line prototype with **no network layer whatsoever** — zero `fetch()` calls, zero API routes, zero server actions. Orders, reservations, catering enquiries, reviews, enrolments and user accounts are simulated with `alert()` and `setTimeout`. Prices, VAT, discounts and delivery fees are computed in the browser from hardcoded strings.

**This backend is not an API being added to a working application. It is the application, being written for the first time.**

---

## Documentation

| Document | Read it when |
|---|---|
| [`PRD.md`](PRD.md) | You need the requirements, scope and success criteria |
| [`docs/FRONTEND_AUDIT.md`](docs/FRONTEND_AUDIT.md) | **First.** What exists, what is fake, and what that implies |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | You are setting up the project or adding an app |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | You are writing models or migrations |
| [`docs/API_SPEC.md`](docs/API_SPEC.md) | You are building or consuming an endpoint |
| [`docs/AUTH.md`](docs/AUTH.md) | You are touching login, sessions, CORS or permissions |
| [`docs/PAYMENTS.md`](docs/PAYMENTS.md) | **Before touching anything payment-related** |
| [`docs/ORDERS_AND_FULFILMENT.md`](docs/ORDERS_AND_FULFILMENT.md) | You are working on orders, the KDS or delivery |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Before launch, and during any security review |
| [`docs/FRONTEND_INTEGRATION.md`](docs/FRONTEND_INTEGRATION.md) | You are wiring `frontend/` to this API |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | You are planning or estimating |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | You are deploying or configuring an environment |
| [`docs/TESTING.md`](docs/TESTING.md) | You are writing tests — especially money tests |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | You want to know *why* something is the way it is |

---

## The rules that override everything else

These are not style preferences. Violating any of them is a production incident waiting to happen.

1. **The server is the only authority on money.** No price, discount, fee, tax or total computed in the browser is ever trusted. Any such field in a request body is ignored.

2. **All money is integer kobo.** ₦1,250.00 is `125000`. `float` is banned in every money path and enforced by CI.

3. **Card data never touches our infrastructure.** The existing `PaymentStep.tsx` card fields must be **deleted, not connected**. Hosted provider checkout only. A CI grep gate fails the build if `cardNumber`/`cardCvv` reappear.

4. **A payment is confirmed by a verified webhook or a server-side verification call — never by the client.** The browser returning from Paystack is a hint to verify, not proof.

5. **No action reports success unless it persisted.** The pattern this replaces is `alert("Reservation submitted!")` with no row written.

6. **Staff change content and prices, not developers.** Menu items, prices, courses, packages and hours live in the database.

7. **Every order state change is an append-only event.** `Order.status` is mutated only through `orders.services.state.transition()`.

---

## Decisions already taken

Agreed with the product owner on 2026-09-11. Rationale in [`docs/DECISIONS.md`](docs/DECISIONS.md).

| Area | Decision |
|---|---|
| Build strategy | Phased — ordering core first; unbuilt features hidden, never faked |
| Payments | Paystack (primary) + Flutterwave (secondary), hosted checkout, plus transfer and cash |
| Auth | django-allauth, session cookies, shared parent domain |
| Realtime | Polling first (15s, ETag-cached); Channels in Phase 3 |
| Staff ops | Django admin + a purpose-built Kitchen Display System |
| Delivery | Own riders, zone-based flat fees |
| Pricing | Backend owns prices; seeds flagged `needs_repricing` and excluded from the API |
| Media | Supabase Storage (S3-compatible) via `django-storages` |
| Notifications | Transactional email only for now |
| Chat | Scripted FAQ bot with ticket handoff — no AI |
| Branches | One branch, modelled for many |
| Deployment | Not yet chosen — options documented |

---

## Open questions blocking work

| # | Question | Blocks |
|---|---|---|
| **OD-1** | **VAT-inclusive or VAT-exclusive pricing?** The published terms say inclusive; the cart adds 7.5% on top. See [`PRD.md`](PRD.md) §7 | Phase 1C pricing engine |
| OD-2 | Real naira prices for the 18 menu items | Gate 1 |
| OD-3 | Real delivery zones, fees and minimum order values | Gate 1 |
| OD-4 | Deployment target | Gate 1 |
| OD-5 | Keep or remove the academy "installment" option | Phase 3 |
| OD-6 | Tip presets — the current ₦2/₦5/₦10 are dollar figures | Gate 1 |

---

## Getting started (once implementation begins)

No Docker, no database server, no Redis — local development runs on a plain
virtualenv (ADR-015).

```bash
cd backend
make venv install            # virtualenv + dependencies
cp .env.example .env         # defaults work as-is
make migrate seed            # SQLite database + baseline branch, hours, role groups
.venv/bin/python manage.py createsuperuser
make run                     # http://localhost:8000
```

Defaults: SQLite, in-memory cache, Celery running tasks eagerly in-process,
email printed to the console. Point `DATABASE_URL` / `REDIS_URL` at real
services when you want them — see `docs/DEPLOYMENT.md` §1a.

| URL | What |
|---|---|
| `http://localhost:8000/api/v1/docs/` | Swagger UI |
| `http://localhost:8000/api/v1/schema/` | OpenAPI 3.1 schema |
| `http://localhost:8000/admin/` | Django admin |

### Quality gates

```bash
make lint          # ruff
make typecheck     # mypy on the money layer
make test          # pytest
make coverage      # 85% overall, 100% on apps/common/money.py
make gate          # PCI card-field gate
make check         # everything CI runs
```

---

## Phase 1 is done when

All eleven criteria in [`PRD.md`](PRD.md) §9 are demonstrated end-to-end. The short version:

A customer registers, verifies their email, browses a staff-priced menu, adds items with real priced modifiers, applies a promo code that validates server-side, pays through Paystack **without any card data reaching our servers**, and watches a real order move from confirmed to delivered on a Kitchen Display the staff are actually using — while every figure on screen came from the server, and **not one `alert()` remains in any submission path**.
