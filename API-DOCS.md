# API reference

Every endpoint the Kuyash Place backend serves, and how to call it.

- **Base URL:** `/api/v1` — locally `http://localhost:8000/api/v1`
- **Interactive:** Swagger UI at `/api/v1/docs/`, ReDoc at `/api/v1/redoc/`, the OpenAPI document (3.0.3) at `/api/v1/schema/`
- **Generated types:** `frontend/lib/api/schema.d.ts`, produced from that schema by `npm run api:sync`

The schema is generated from the code, so **Swagger is the authority on exact request and response fields**. This page is the map: what exists, who may call it, which headers to send, and how the pieces fit into a real journey.

---

## Contents

1. [Conventions](#1-conventions) · 2. [Authentication](#2-authentication) · 3. [Errors](#3-errors) · 4. [Rate limits](#4-rate-limits)
5. [Endpoints](#5-endpoints) · 6. [Worked examples](#6-worked-examples) · 7. [WebSockets](#7-websockets) · 8. [Keeping this accurate](#8-keeping-this-accurate)

---

## 1. Conventions

### Money

Every amount is an **integer number of kobo** wrapped in an object:

```json
{ "amount": 1090000, "currency": "NGN", "display": "₦10,900.00" }
```

`amount` is ₦10,900.00 expressed as kobo. **Render `display`; never do arithmetic on `amount` in a client.** The server is the only authority on prices, discounts, fees, tax and totals — any such field in a request body is ignored. A CI gate fails the build if a frontend component computes money.

### Requests and responses

- JSON in, JSON out (`Content-Type: application/json`), UTF-8.
- Timestamps are ISO 8601 with an offset; the branch's own timezone is `Africa/Lagos`.
- Identifiers are either UUIDs or human references such as `KYS-7Q2M-4813`.
- Unknown fields in a request body are ignored rather than rejected.

### Custom headers

| Header | Sent on | Why |
|---|---|---|
| `X-Cart-Token` | cart calls, reorder | Identifies a guest's cart. The API issues it on the first write and returns it on every cart response |
| `X-Guest-Token` | `GET /orders/{reference}/` and its actions | Lets a guest track the order they just placed, without an account |
| `X-Reservation-Token` | guest booking lookups | Same idea for reservations |
| `X-Enrolment-Token` | guest academy enrolments | Same idea for course enrolments |
| `X-Chat-Token` | chat session calls | Same idea for a support conversation |
| `Idempotency-Key` | `POST /orders/`, `POST /reservations/`, `POST /academy/enrolments/` | **Required.** A repeated key returns the first result with `Idempotency-Replayed: true` instead of creating a second order, booking or enrolment |
| `X-CSRFToken` | every write from a browser session | Echo of the `kuyash_csrftoken` cookie |
| `If-None-Match` | `GET /orders/{reference}/` | Returns `304` when the order has not changed |

### Pagination

Two envelopes, both with `results`:

```json
{ "results": [ … ], "next": "…?cursor=cD0y", "previous": null }
```

- **Cursor** (`?cursor=`, `?limit=`) for append-only feeds: order history, the points ledger. Page boundaries cannot shift when a new row arrives.
- **Page** (`?page=`, `?limit=`) for sortable collections such as the menu and reviews; it also returns `count`.

`limit` defaults to 20 and caps at 100.

---

## 2. Authentication

Sessions are **cookie-based** (`kuyash_session`), not tokens. The frontend and API must share a parent domain in production, and the browser must send credentials on every call.

### Signing in

```bash
# 1. Seed the CSRF cookie
curl -c jar.txt http://localhost:8000/api/v1/auth/csrf/

# 2. Sign in, echoing the CSRF cookie back in the header
curl -b jar.txt -c jar.txt -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep kuyash_csrftoken jar.txt | cut -f7)" \
  -d '{"email": "ada@example.com", "password": "correct-horse-battery-staple"}'

# 3. Who am I?
curl -b jar.txt http://localhost:8000/api/v1/auth/session/
```

A write without a valid `X-CSRFToken` is refused with `permission_denied` (403), signed in or not — the sign-in endpoints enforce it too, so a page on another site cannot sign a visitor into an attacker's account.

Registration requires `email`, `password`, `full_name`, `phone` and `accept_terms: true`. **Email verification is mandatory**: registering does not sign you in; following the emailed link (`POST /auth/verify-email/` with its `key`) does.

Social sign-in is handled by django-allauth's headless endpoints under `/_allauth/`, which are outside this schema. See [`backend/docs/AUTH.md`](backend/docs/AUTH.md).

### Guests

Checkout and order tracking work without an account. A guest's cart is identified by `X-Cart-Token`, and the order they place returns a `guest_token` to send back as `X-Guest-Token`. Signing in later merges the guest cart (`POST /cart/merge/`).

### Who may call what

| Audience | How it is decided | Examples |
|---|---|---|
| Anyone | no session needed | menu, gallery, FAQ, legal pages, opening hours, placing an order |
| Signed-in customer | session cookie | account, addresses, order history, wishlist, loyalty, reviews |
| Kitchen | `kitchen` or `managers` group | everything under `/kds/` |
| Manager | `managers` group | refunds, reports, moderation, overdue enquiries, open tickets |
| Provider | signed webhook, no session | `/webhooks/paystack/`, `/webhooks/flutterwave/` |

An object that is not yours answers **404, never 403** — the API does not confirm that someone else's order exists.

---

## 3. Errors

Every error is an RFC 7807 problem document with a stable `code` to branch on:

```json
{
  "type": "https://api.kuyashplace.com/errors/promo-invalid",
  "title": "That promo code cannot be applied",
  "status": 422,
  "code": "promo_invalid",
  "detail": "This code has already been used."
}
```

Validation failures carry `errors` keyed by field name. Throttled responses carry `retry_after` seconds and a `Retry-After` header.

| Code | Status | Means |
|---|---|---|
| `validation_error` | 400 | One or more fields were invalid; see `errors` |
| `idempotency_key_required` | 400 | Send an `Idempotency-Key` header |
| `authentication_required` | 401 | Sign in first |
| `permission_denied` | 403 | Signed in but not allowed — **also what a missing or stale `X-CSRFToken` returns** |
| `method_not_allowed` | 405 | Wrong verb for that path |
| `malformed_request` | 400 | The body was not valid JSON |
| `unsupported_media_type` | 415 | Send `Content-Type: application/json` |
| `not_found` | 404 | No such object — or it isn't yours |
| `payment_failed` | 402 | No provider would start the payment |
| `price_changed` | 409 | Prices moved during checkout; re-quote and confirm |
| `item_unavailable` | 409 | Something in the cart sold out |
| `branch_closed` | 409 | The restaurant is not accepting orders |
| `illegal_transition` | 409 | That order status change is not allowed |
| `idempotency_conflict` | 409 | An identical request is still in flight |
| `promo_invalid` | 422 | Code unknown, expired, used up, or not valid for this basket |
| `outside_delivery_area` | 422 | The address is outside every delivery zone |
| `below_minimum_order` | 422 | Basket is under the minimum for that zone |
| `rate_limited` | 429 | Too many requests; wait `retry_after` seconds |
| `internal_error` | 500 | Our fault; nothing leaked about why |

---

## 4. Rate limits

Anonymous callers get 100 requests/minute, signed-in users 300/minute, plus these per-endpoint limits (writes only — reading your own orders never spends the order-placement allowance):

| Endpoint | Limit |
|---|---|
| `POST /auth/login/` | 5/min per IP, 10/hour per email |
| `POST /auth/register/` | 3/hour |
| `POST /auth/password/reset/`, `/resend-verification/` | 3/hour |
| `POST /orders/` | 10/hour |
| `POST /cart/promo/` | 10/min |
| `POST /support/contact/` | 3/hour |
| `POST /catering/enquiries/` | 5/hour |
| `POST /reviews/` | 10/hour · helpful votes 60/hour |
| Chat: sessions / messages / escalate | 20/hour · 30/min · 3/hour |
| `POST /academy/enrolments/` | 10/hour |

Limits key on the client's real address, which behind a proxy means `TRUSTED_PROXY_COUNT` must match how many proxies sit in front of Django.

---

## 5. Endpoints

103 paths, 118 operations. Auth column: **—** public · **user** signed in · **kitchen** kitchen or managers · **manager** managers only.

### Restaurant information

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/core/branch/` | — | Address, phone, currency, VAT policy, whether orders are being accepted |
| GET | `/core/opening-hours/` | — | Per weekday and service |
| GET | `/core/settings/` | — | Site settings: social links, hero figures, founding year |
| GET | `/core/legal/` · `/core/legal/{slug}/` | — | Terms, privacy, refunds — Markdown written in the admin |
| GET | `/core/team/` · `/core/awards/` | — | About-page content |

### Menu

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/catalog/categories/` | — | With item counts |
| GET | `/catalog/dietary-tags/` | — | Vegan, allergens, … |
| GET | `/catalog/featured/` | — | Up to 12, most popular first |
| GET | `/catalog/items/` | — | `?category=&search=&dietary=&min_price=&max_price=&min_rating=&sort=&available_only=&page=&limit=` |
| GET | `/catalog/items/{slug}/` | — | Variants, modifier groups, photos, allergens |

Dishes still flagged `needs_repricing`, sold out, or outside their availability window are not returned.

### Cart

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/cart/` | — | Send `X-Cart-Token` as a guest; returns lines and server totals |
| DELETE | `/cart/` | — | Empty it |
| POST | `/cart/items/` | — | `{menu_item, quantity, variant?, modifiers: [{modifier}], special_instructions?}` |
| PATCH/DELETE | `/cart/items/{id}/` | — | Change quantity or remove a line |
| POST/DELETE | `/cart/promo/` | — | `{code}`; validated server-side, with usage limits |
| PATCH | `/cart/fulfilment/` | — | `{fulfilment_type: "delivery"\|"pickup", delivery_address?, tip?}` |
| POST | `/cart/merge/` | user | Merge the guest cart named by `X-Cart-Token` into the account's |
| POST | `/cart/quote/` | — | Price a configuration without adding it |

Totals always come back as `subtotal`, `discount`, `delivery_fee`, `service_charge`, `vat`, `tip`, `grand_total`.

### Orders

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/orders/` | — | **`Idempotency-Key` required.** `{payment_method, expected_total, customer_note?, guest?{full_name,email,phone}}` |
| GET | `/orders/mine/` | user | Cursor-paginated history |
| GET | `/orders/{reference}/` | — | Owner, or `X-Guest-Token`. Supports `If-None-Match` |
| POST | `/orders/{reference}/cancel/` | — | Allowed until the kitchen starts cooking |
| POST | `/orders/{reference}/reorder/` | user | Rebuilds the cart at today's prices; reports what changed |
| GET | `/orders/{reference}/receipt/` | — | PDF |

`expected_total` is a guard, not a price: if the server's total differs from what the customer was shown, the order is refused rather than charged at a figure they never saw.

### Payments

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/payments/initialise/` | — | `{order, save_card?}` → `authorization_url` for the provider's hosted page |
| GET | `/payments/verify/{reference}/` | — | Server-to-server confirmation; the browser's return is only a hint |
| POST | `/payments/refund/{reference}/` | manager | Full or partial |
| GET | `/payments/methods/` | user | Saved cards — brand, last four and expiry only |
| DELETE | `/payments/methods/{id}/` | user | Forget a card |
| POST | `/payments/methods/{id}/set-default/` | user | |
| POST | `/webhooks/paystack/` · `/webhooks/flutterwave/` | signature | Provider callbacks; forged signatures are recorded and rejected |

**No card number, CVV or expiry ever reaches this API.** Payment is a redirect to the provider's hosted page.

### Kitchen display (`kitchen`)

| Method | Path | Notes |
|---|---|---|
| GET | `/kds/orders/` | The live queue, oldest first, plus `reject_reasons` |
| GET | `/kds/summary/` | Counts by status, open tickets, today's revenue |
| GET | `/kds/riders/` | Active riders, on shift first |
| GET | `/kds/items/` | Every priced dish **including sold-out ones** |
| POST | `/kds/orders/{reference}/accept/` | → confirmed |
| POST | `/kds/orders/{reference}/reject/` | `{reason: "<code>", note?}` — the code must come from `reject_reasons` |
| POST | `/kds/orders/{reference}/advance/` | `{to: "preparing"\|"ready"\|"out_for_delivery"\|"delivered"}` |
| POST | `/kds/orders/{reference}/assign-rider/` | `{rider: "<id>"}` |
| POST | `/kds/items/{slug}/availability/` | `{is_available_now: false}` — "86 this dish" |

### Account

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/PATCH | `/accounts/me/` | user | Profile and preferences |
| DELETE | `/accounts/me/` | user | Erasure under the NDPR: anonymised, session ended |
| GET/POST | `/accounts/addresses/` | user | Address book; the first one becomes the default |
| GET/PUT/PATCH/DELETE | `/accounts/addresses/{id}/` | user | Scoped to the caller |
| POST | `/accounts/addresses/{id}/set-default/` | user | |
| GET/POST | `/wishlist/` · POST `/wishlist/sync/` · DELETE `/wishlist/{slug}/` | user | `sync` merges a guest's local list on sign-in |

### Auth

| Method | Path | Notes |
|---|---|---|
| GET | `/auth/csrf/` | Seed the CSRF cookie before any write |
| GET | `/auth/session/` | Current user, or `null` |
| POST | `/auth/register/` · `/login/` · `/logout/` | |
| POST | `/auth/verify-email/` · `/resend-verification/` | Verification is mandatory |
| POST | `/auth/password/reset/` · `/reset/confirm/` · `/change/` | Reset replies the same way whether or not the address exists |

### Reservations

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/reservations/areas/` | — | Seating areas |
| GET | `/reservations/availability/` | — | `?date=&party_size=&area=` — bookable slots |
| POST | `/reservations/` | — | **`Idempotency-Key` required**; a table cannot be double-booked |
| GET | `/reservations/mine/` | user | |
| GET/PATCH | `/reservations/{reference}/` | — | Guests send `X-Reservation-Token`; PATCH reschedules |
| POST | `/reservations/{reference}/cancel/` | — | |
| GET | `/reservations/book/` | staff | Today's book, for front of house |

### Catering, support and chat

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/catering/packages/` | — | |
| POST | `/catering/enquiries/` | — | Opens an enquiry with an SLA timer |
| GET | `/catering/enquiries/{reference}/` | — | The owner or staff; a guest proves it with `?email=` the address they enquired from. Anyone else gets 404 |
| GET | `/catering/enquiries/overdue/` | manager | Enquiries past their SLA |
| POST | `/support/contact/` | — | Persists a message and opens a ticket |
| GET | `/support/faq/` | — | Powers `/help` and the assistant |
| POST | `/support/chat/sessions/` | — | Start a conversation; returns a chat token |
| GET | `/support/chat/sessions/{id}/` | — | Reopen with `X-Chat-Token` |
| POST | `/support/chat/sessions/{id}/messages/` | — | Scripted FAQ assistant — no AI |
| POST | `/support/chat/sessions/{id}/escalate/` | — | Hands the conversation to a person |
| GET | `/support/tickets/` | user | Your own tickets |
| GET/POST | `/support/tickets/{reference}/` | — | The owner or staff; a guest proves it with `?email=`. POST adds a reply |
| GET | `/support/tickets/open/` | staff | The staff queue (any staff member, kitchen included) |

### Reviews, gallery, academy and loyalty

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/reviews/?item={slug}` | — | Published reviews, page-paginated |
| POST | `/reviews/` | user | Only for a dish you actually received |
| GET/PATCH/DELETE | `/reviews/{id}/` | user | Editable for a limited window |
| POST | `/reviews/{id}/helpful/` | — | One vote per person |
| GET | `/reviews/pending/` · POST `/reviews/{id}/moderate/` | manager | Moderation queue |
| GET | `/gallery/` · `/gallery/{id}/` | — | `?category=&tag=&featured=`; detail includes neighbours for the lightbox |
| GET | `/academy/courses/` · `/{slug}/` · `/{slug}/cohorts/` | — | Classes with seats remaining |
| POST | `/academy/enrolments/` | — | **`Idempotency-Key` required.** Books a seat and holds it while payment is pending |
| GET | `/academy/enrolments/mine/` · `/{reference}/` | user or token | |
| POST | `/academy/enrolments/{reference}/pay/` | — | Hosted checkout, same providers as orders |
| GET | `/academy/enrolments/{reference}/certificate/` | — | PDF, once the course is complete |
| GET | `/academy/payments/verify/{reference}/` | — | |
| GET | `/loyalty/tiers/` | — | The programme and its rules |
| GET | `/loyalty/account/` · `/ledger/` | user | Balance, tier, progress; the ledger is the source of truth |
| GET | `/loyalty/rewards/` | — | Catalogue with what you can afford |
| POST | `/loyalty/rewards/{id}/redeem/` | user | Applies a reward to the cart |
| DELETE | `/loyalty/rewards/applied/` | user | Takes it off again |

### Reports (`manager`)

| Method | Path | Notes |
|---|---|---|
| GET | `/reports/sales/` | `?from=&to=&export=csv` — gross, refunds, net, daily totals |
| GET | `/reports/items/` | Best-selling dishes |
| GET | `/reports/peak-hours/` | Orders by weekday and hour |
| GET | `/reports/riders/` | Deliveries and times per rider |

### Operational

| Method | Path | Notes |
|---|---|---|
| GET | `/health/` | **Not under `/api/v1`.** Database, cache and scheduler status; 503 when the database or cache fails |

---

## 6. Worked examples

### A guest buys lunch

```bash
API=http://localhost:8000/api/v1

# 1. Add a dish. The response header carries the cart token.
TOKEN=$(curl -s -D - -o /dev/null -X POST $API/cart/items/ \
  -H "Content-Type: application/json" \
  -d '{"menu_item": "classic-smash-burger", "quantity": 2}' \
  | grep -i '^x-cart-token:' | cut -d' ' -f2 | tr -d '\r')

# 2. Choose delivery and see the server's totals.
curl -s -X PATCH $API/cart/fulfilment/ -H "X-Cart-Token: $TOKEN" \
  -H "Content-Type: application/json" -d '{"fulfilment_type": "pickup"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["totals"]["grand_total"]["display"])'

# 3. Place the order. The idempotency key makes a double tap harmless.
ORDER=$(curl -s -X POST $API/orders/ -H "X-Cart-Token: $TOKEN" \
  -H "Content-Type: application/json" -H "Idempotency-Key: $(uuidgen)" \
  -d '{"payment_method": "card", "expected_total": 2240000,
       "guest": {"full_name": "Ada Obi", "email": "ada@example.com", "phone": "+2348012345678"}}')

REF=$(echo "$ORDER" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reference"])')
GUEST=$(echo "$ORDER" | python3 -c 'import json,sys; print(json.load(sys.stdin)["guest_token"])')

# 4. Start the payment and send the customer to the provider's page.
curl -s -X POST $API/payments/initialise/ -H "Content-Type: application/json" \
  -d "{\"order\": \"$REF\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["authorization_url"])'

# 5. Track it afterwards.
curl -s $API/orders/$REF/ -H "X-Guest-Token: $GUEST"
```

### The kitchen works the order

```bash
# Signed in as kitchen staff (session cookie in jar.txt)
curl -s -b jar.txt $API/kds/orders/                       # the queue, plus reject_reasons
curl -s -b jar.txt -X POST $API/kds/orders/$REF/accept/ -H "X-CSRFToken: …"
curl -s -b jar.txt -X POST $API/kds/orders/$REF/advance/ -H "X-CSRFToken: …" \
  -H "Content-Type: application/json" -d '{"to": "preparing"}'
curl -s -b jar.txt -X POST $API/kds/items/suya/availability/ -H "X-CSRFToken: …" \
  -H "Content-Type: application/json" -d '{"is_available_now": false}'
```

### Confirming a payment

Never trust the browser's return. When the customer lands back on the callback URL, call:

```bash
curl -s $API/payments/verify/$PAYMENT_REFERENCE/
```

The order also settles on its own from the provider's signed webhook, and a scheduled task reconciles anything whose webhook never arrived — so a customer who closes the tab still gets their food.

---

## 7. WebSockets

Same host, `ws://` (or `wss://`), outside `/api/v1`:

| Path | Who | Messages |
|---|---|---|
| `ws/orders/{reference}/` | the owner, or a guest who sends `{"type":"auth","token":"<guest token>"}` as the first message | `{"type":"order","order":{…}}` on every change |
| `ws/kds/` | kitchen or managers, by session | `{"type":"queue","orders":[…]}` on join, then `{"type":"ticket","ticket":{…}}` per change |

Both carry exactly the payloads their REST equivalents return. Sockets are an optimisation, not a requirement: the order page falls back to polling every 15 seconds and the kitchen screen every 10, so nothing breaks when the connection drops. Origins are checked against `CORS_ALLOWED_ORIGINS`.

---

## 8. Keeping this accurate

The OpenAPI document is generated from the code, so it cannot drift:

```bash
cd frontend && npm run api:sync     # regenerates lib/api/openapi.yml and schema.d.ts
```

`api:sync` runs `manage.py spectacular --validate --fail-on-warn`, which fails on an invalid or under-described schema. Every operation carries a summary and a tag; add `@extend_schema(summary=…, tags=[…])` to any new view, and re-run `api:sync` so the committed schema and the generated types match the code.

When you add or change an endpoint, update this page's table for that area as well — it is the map, while Swagger is the detail.
