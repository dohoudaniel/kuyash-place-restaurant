# Architecture — Kuyash Place Backend

**Stack:** Django 5.x · Django REST Framework · PostgreSQL 16 · Redis 7 · Celery · django-allauth · django-storages (Supabase Storage)

---

## 1. Shape of the system

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser                                                          │
│  ┌────────────────────────┐        ┌──────────────────────────┐  │
│  │ Next.js 16 (frontend/) │        │ Paystack / Flutterwave   │  │
│  │  - RSC for static      │        │ hosted checkout iframe   │  │
│  │  - Client components   │        │ (card data goes HERE,    │  │
│  │  - typed API client    │        │  never to our servers)   │  │
│  └───────────┬────────────┘        └────────────┬─────────────┘  │
└──────────────┼──────────────────────────────────┼────────────────┘
               │ session cookie (HttpOnly)        │
               │ same parent domain               │ redirect + webhook
               ▼                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│  Django (ASGI or WSGI)                                            │
│                                                                   │
│   api/v1/  ──▶  DRF ViewSets ──▶ Services ──▶ Models              │
│                      │               │                            │
│                      │               └─▶ pricing engine (kobo)    │
│                      │               └─▶ order state machine      │
│                      │               └─▶ payment providers        │
│                      │                                            │
│   /admin/  ──▶  Django admin (staff content + pricing + refunds)  │
│   /api/v1/kds/ ──▶ Kitchen Display endpoints (staff-only)         │
│   /api/v1/webhooks/ ──▶ signature-verified, idempotent            │
└────────┬────────────────────────┬───────────────────┬────────────┘
         │                        │                   │
         ▼                        ▼                   ▼
   ┌───────────┐            ┌──────────┐       ┌──────────────┐
   │ Postgres  │            │  Redis   │       │  Supabase    │
   │  (truth)  │            │ cache +  │       │  Storage     │
   │           │            │ celery   │       │  (S3 API)    │
   └───────────┘            └────┬─────┘       └──────────────┘
                                 │
                           ┌─────▼──────┐
                           │  Celery    │  email, webhooks retry,
                           │  workers   │  reconciliation, reports
                           │  + beat    │
                           └────────────┘
```

**Key property:** the frontend and the payment provider are the only things that ever see card data, and they never see each other's secrets. Our servers see a provider reference and an amount.

---

## 2. Repository layout

```
backend/
├── PRD.md
├── docs/                          # this documentation set
├── manage.py
├── pyproject.toml                 # deps via uv or poetry; ruff + mypy config
├── .env.example
├── docker-compose.yml             # postgres + redis + web + worker + beat
├── Dockerfile
│
├── config/                        # project, not an app
│   ├── settings/
│   │   ├── base.py                # everything shared
│   │   ├── dev.py                 # DEBUG, console email, relaxed CORS
│   │   ├── prod.py                # hardened; fails loudly on missing env
│   │   └── test.py                # in-memory, eager celery, dummy providers
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
│
└── apps/
    ├── common/                    # shared primitives — no app depends upward
    │   ├── models.py              # UUIDModel, TimeStampedModel, SoftDeleteModel
    │   ├── fields.py              # MoneyField (kobo), PhoneField
    │   ├── money.py               # Money value object, VAT maths, formatting
    │   ├── pagination.py
    │   ├── permissions.py         # IsStaff, IsKitchen, IsRider, IsOwnerOrStaff
    │   ├── exceptions.py          # DomainError → RFC 7807 problem responses
    │   ├── idempotency.py         # Idempotency-Key middleware + store
    │   └── admin.py               # base admin mixins
    │
    ├── core/                      # Branch, SiteSettings, OpeningHours, legal pages
    ├── accounts/                  # User, Profile, Address, allauth adapters
    ├── catalog/                   # Category, MenuItem, Variant, ModifierGroup, Modifier, Tag
    ├── carts/                     # Cart, CartItem, cart merge, repricing
    ├── promotions/                # PromoCode, PromoRedemption, rules engine
    ├── orders/                    # Order, OrderItem, OrderStatusEvent, state machine, KDS
    ├── payments/                  # PaymentTransaction, Refund, providers/, webhooks
    ├── delivery/                  # DeliveryZone, RiderProfile, DeliveryAssignment
    ├── reservations/              # Table, Reservation, availability engine     [Phase 2]
    ├── catering/                  # CateringPackage, CateringEnquiry            [Phase 2]
    ├── support/                   # ContactMessage, Ticket, FaqEntry, ChatSession [Phase 2-3]
    ├── reviews/                   # Review, moderation, aggregates              [Phase 3]
    ├── academy/                   # Instructor, Course, Cohort, Enrolment       [Phase 3]
    ├── loyalty/                   # LoyaltyAccount, PointsLedger, Tier, Reward  [Phase 3]
    ├── gallery/                   # GalleryImage, GalleryTag                    [Phase 3]
    └── notifications/             # EmailTemplate, Notification outbox, tasks
```

### 2.1 Dependency rule

Apps may import **downward only**:

```
common  ←  core  ←  accounts  ←  catalog  ←  carts  ←  promotions  ←  orders  ←  payments
                                                                          ↑
                                              delivery, loyalty, reviews ─┘
```

No app imports from an app to its right. Where a right-hand app must react to a left-hand one (loyalty awarding points when an order is delivered), it subscribes to a **domain signal** rather than being imported. This keeps `orders` ignorant of `loyalty`, which is what lets Phase 3 land without touching Phase 1 code.

---

## 3. Layering inside an app

```
urls.py       →  routes only
views.py      →  DRF ViewSets: authz, deserialize, call service, serialize. No business logic.
serializers.py→  shape in / shape out. Validation that is about *format*.
services.py   →  ALL business logic. Transactions. Domain validation. Returns domain objects.
selectors.py  →  read queries with the right select_related/prefetch_related.
models.py     →  persistence + invariants that are truly per-row (constraints, clean()).
tasks.py      →  Celery entry points. Thin wrappers over services.
signals.py    →  domain events emitted, never business logic performed.
admin.py      →  staff UI.
```

**The rule that matters:** a view must never contain an `if` that decides something commercial. If you can't test a rule without an HTTP request, it's in the wrong file.

### 3.1 Why services, not fat models

The pricing engine touches `catalog`, `carts`, `promotions`, `delivery` and `core` (VAT policy) simultaneously. That calculation cannot live on any one model without that model importing its siblings. It lives in `apps/carts/services/pricing.py` as a pure function over loaded data, which is also what makes it unit-testable without the database.

---

## 4. Money — the one non-negotiable convention

The frontend currently does this:

```tsx
const priceValue = parseFloat(item.price.replace(/[^\d.]/g, ""));  // ❌
const tax = (subtotal - discount) * 0.075;                          // ❌
```

The backend will never do anything resembling it.

### 4.1 Rules

1. **All money is an integer count of kobo.** ₦1,250.00 is `125000`. Stored in `PositiveBigIntegerField` (or `BigIntegerField` where negatives are legal, e.g. ledger entries).
2. **`float` is banned in any money path.** Ruff/flake8 rule + code review. Where a ratio is unavoidable (percentage discounts, VAT extraction), use `decimal.Decimal` for the intermediate and round to integer kobo immediately.
3. **Rounding is `ROUND_HALF_UP`, applied once, at the last step of each component** — not accumulated across line items.
4. **The API returns both the integer and a formatted string:**

```json
{ "subtotal": { "amount": 1250000, "currency": "NGN", "display": "₦12,500.00" } }
```

The frontend renders `display` and never formats currency itself. This kills an entire class of "the cart says ₦12,500 but you were charged ₦12,500.01" bug.

5. **Every total is recomputed server-side at order placement**, even though the cart already computed it. The cart's number is a quote; the order's number is the charge.

### 4.2 VAT

Per `PRD.md` §7, VAT direction is a branch-level setting.

```python
# prices_include_vat = True  (default, Option A)
vat = round(gross * Decimal("7.5") / Decimal("107.5"))
net = gross - vat                       # customer pays `gross` — the menu price

# prices_include_vat = False (Option B)
vat = round(net * Decimal("7.5") / Decimal("100"))
gross = net + vat                       # customer pays more than the menu price
```

Per-item `tax_class` (`standard` / `zero_rated` / `exempt`) means VAT is summed per line, not applied to the order subtotal. That matters the moment a zero-rated item enters the menu.

---

## 5. Request lifecycle — placing an order

The single most important path in the system.

```
1. POST /api/v1/orders/            Idempotency-Key: <uuid>
   │
2. IdempotencyMiddleware
   │  ├─ key seen + completed?  → replay the stored response, do nothing else
   │  └─ key seen + in flight?  → 409 Conflict
   │
3. OrderViewSet.create
   │  └─ serializer validates SHAPE only (address id, fulfilment type, payment method)
   │     Any `price`, `total` or `discount` in the body is ignored.
   │
4. orders.services.place_order()   ── inside transaction.atomic() ──
   │  ├─ select_for_update() the cart
   │  ├─ assert the branch is open and accepting orders          (DEL-5)
   │  ├─ reprice every line from live catalogue data             (CART-7)
   │  ├─ assert every item is_available_now                      (CAT-7)
   │  ├─ re-validate the promo code and its limits               (PROMO-5)
   │  ├─ resolve the delivery zone and fee from the address      (DEL-1/2)
   │  ├─ compute VAT per line by tax class                       (CAT-9)
   │  ├─ assert the client's displayed total matches, or 409     ← price-changed guard
   │  ├─ create Order + OrderItems as an immutable SNAPSHOT      (ORD-3)
   │  ├─ generate a random, non-sequential reference             (ORD-1)
   │  ├─ write PromoRedemption (pending)                         (PROMO-4)
   │  ├─ write OrderStatusEvent(→ pending_payment)               (ORD-8)
   │  └─ mark the cart converted — DO NOT delete it yet          (ORD-4)
   │
5. payments.services.initialise()
   │  └─ call Paystack/Flutterwave init → returns authorization_url + reference
   │
6. 201 Created
   {  "reference": "KYS-7Q2XF9",
      "status": "pending_payment",
      "payment": { "provider": "paystack", "authorization_url": "https://..." },
      "totals": { ... } }
   │
7. Frontend redirects the browser to authorization_url.
   Card data flows browser → provider. We never see it.
   │
8. Provider → POST /api/v1/webhooks/paystack/   (signature verified, idempotent)
   │  └─ verify signature → verify amount+currency against the order  (PAY-5)
   │     → transition order to `paid` → emit order_paid signal
   │        ├─ notifications: queue confirmation email
   │        ├─ carts: NOW clear the cart
   │        └─ KDS: order becomes visible to the kitchen
   │
9. Customer polls GET /api/v1/orders/KYS-7Q2XF9/ every 15s (ETag-cached).
```

**Step 8 is where the order becomes real — not step 6, and never on a client callback.** The browser redirect back from the provider is treated as a *hint* to re-verify, never as proof of payment.

---

## 6. Cross-cutting concerns

### 6.1 Idempotency

`Idempotency-Key` is **required** on `POST /orders/`, `POST /payments/initialise/`, `POST /reservations/` and `POST /academy/enrolments/`. Keys are stored in Redis with the serialized response for 24 hours. This is the mechanism that makes the current frontend's double-tap-able "Confirm Order" button safe.

### 6.2 Errors

All errors are RFC 7807 problem documents, with a machine-readable `code` the frontend switches on:

```json
{
  "type": "https://api.kuyashplace.com/errors/item-unavailable",
  "title": "An item in your cart is no longer available",
  "status": 409,
  "code": "item_unavailable",
  "detail": "Chef's Special Pasta sold out while you were checking out.",
  "items": ["chefs-special-pasta"]
}
```

Never a bare 500, and never a stack trace in production.

### 6.3 Domain events

`django.dispatch` signals defined in `apps/<app>/signals.py`:

`order_placed` · `order_paid` · `order_status_changed` · `order_refunded` · `payment_failed` · `reservation_confirmed` · `enrolment_completed` · `review_approved`

Receivers live in the *consuming* app. `loyalty` listens for `order_status_changed(to="delivered")`; `orders` has no idea loyalty exists.

### 6.4 Caching

| What | Where | Invalidation |
|---|---|---|
| Menu list/detail | Redis, 5 min | Explicit bust on catalogue save |
| Opening hours / site settings | Redis, 1 hour | Bust on save |
| Delivery zones | Redis, 1 hour | Bust on save |
| Order status (polling) | `ETag` on the response | Bumped by `OrderStatusEvent` creation |

Carts, orders and anything money-bearing are **never** cached.

### 6.5 Background work (Celery)

| Task | Trigger |
|---|---|
| `send_email` | domain signal |
| `verify_pending_payments` | beat, every 10 min — catches missed webhooks |
| `expire_stale_orders` | beat, hourly — `pending_payment` older than 30 min |
| `recalculate_item_ratings` | on review approval |
| `award_loyalty_points` | on `order_status_changed(delivered)` |
| `send_reservation_reminders` | beat, daily |
| `nightly_sales_report` | beat |

`verify_pending_payments` is not optional. It is the safety net for the day the webhook endpoint is unreachable and money has changed hands.

### 6.6 Media

`django-storages` S3 backend pointed at **Supabase Storage**:

```python
AWS_S3_ENDPOINT_URL   = env("SUPABASE_S3_ENDPOINT")   # https://<ref>.supabase.co/storage/v1/s3
AWS_STORAGE_BUCKET_NAME = env("SUPABASE_BUCKET")      # e.g. "kuyash-media"
AWS_S3_REGION_NAME    = env("SUPABASE_REGION")
AWS_ACCESS_KEY_ID     = env("SUPABASE_S3_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = env("SUPABASE_S3_SECRET_KEY")
AWS_S3_ADDRESSING_STYLE = "path"                       # Supabase requires path style
AWS_QUERYSTRING_AUTH  = False                          # public read for menu/gallery
```

Uploads are validated for content type and size, and resized into derivatives (`thumb` 400px, `card` 800px, `full` 1600px) by a Celery task. Public URLs are returned by the API — which retires `lib/assets/images.ts` and the hand-maintained `IMAGES` registry entirely.

> The frontend must add the Supabase hostname to `next.config.ts` → `images.remotePatterns`. It is currently an empty config, so remote images will not render.

---

## 7. Conventions

| Topic | Convention |
|---|---|
| Primary keys | `UUIDv4`, never sequential integers on anything customer-visible |
| Public identifiers | `slug` for catalogue, opaque `reference` for orders |
| Timestamps | `created_at` / `updated_at` on every model via `TimeStampedModel`; UTC in DB |
| Deletions | Soft delete (`is_active`) for catalogue and content; hard delete never for financial records |
| Naming | Models singular (`MenuItem`); API collections plural (`/menu-items/`) |
| API style | `kebab-case` paths, `snake_case` JSON bodies |
| Versioning | URL prefix `/api/v1/` |
| Enums | `models.TextChoices`, with the DB value never a display string |
| Migrations | One logical change per migration; reversible; data migrations separate from schema |
| Config | `django-environ`; `prod.py` raises on any missing required variable at import |
| Code style | `ruff` (format + lint), `mypy --strict` on `services/` and `money.py` |

---

## 8. What the frontend must stop doing

Restating the architectural contract, because it is the thing most likely to be violated during integration:

| The frontend must NOT | Because |
|---|---|
| Calculate any price, discount, VAT, fee or total | The server is the only authority (P1) |
| Format currency | The server returns `display` strings |
| Hold a menu, promo or course list in a `.ts` file | Staff edit these in admin (P4) |
| Derive an item ID from a name or image key | Identity is a server-owned UUID/slug (CART-3) |
| Send a price, total or discount in a request body | It will be ignored |
| Collect a card number, expiry or CVV | PCI-DSS (P3) |
| Treat a payment redirect as confirmation | Only a verified webhook confirms (PAY-3) |
| Report success before a 2xx response | No fake success (P2) |

See [`FRONTEND_INTEGRATION.md`](FRONTEND_INTEGRATION.md) for the file-by-file change list.
