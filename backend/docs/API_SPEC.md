# API Specification — Kuyash Place Backend

**Base URL:** `/api/v1/`
**Auth:** session cookie (HttpOnly, Secure, SameSite=Lax) — see [`AUTH.md`](AUTH.md)
**Content type:** `application/json`; bodies `snake_case`; paths `kebab-case`
**Schema:** auto-generated OpenAPI 3.1 at `/api/v1/schema/`, Swagger UI at `/api/v1/docs/`

---

## 0. Conventions

### 0.1 Money is always an object

Never a bare number, never a string:

```json
{ "amount": 1250000, "currency": "NGN", "display": "₦12,500.00" }
```

`amount` is **integer kobo**. `display` is server-formatted. **The frontend renders `display` and never does arithmetic on `amount`.**

### 0.2 Errors are RFC 7807 problem documents

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

Field-level validation errors add `errors`:

```json
{ "status": 400, "code": "validation_error",
  "errors": { "phone": ["Enter a valid Nigerian phone number."] } }
```

| Code | Status | Meaning |
|---|---|---|
| `validation_error` | 400 | Field validation failed |
| `authentication_required` | 401 | No valid session |
| `email_not_verified` | 403 | Account exists but unverified |
| `permission_denied` | 403 | Authenticated but not allowed |
| `not_found` | 404 | |
| `idempotency_conflict` | 409 | Same key, request still in flight |
| `price_changed` | 409 | Cart repriced since the client last read it |
| `item_unavailable` | 409 | Item went out of stock |
| `branch_closed` | 409 | Outside opening hours |
| `promo_invalid` | 422 | Code expired, exhausted or inapplicable |
| `outside_delivery_area` | 422 | Address resolves to no zone |
| `below_minimum_order` | 422 | |
| `payment_failed` | 402 | Provider declined |
| `rate_limited` | 429 | `Retry-After` header included |

### 0.3 Pagination

Two styles, chosen by what the collection is.

**Append-only feeds** (orders, ledger entries) use **cursor** pagination — a new
row arriving mid-listing cannot shift page boundaries:

```
GET /orders/?limit=20&cursor=<opaque>
{ "results": [...], "next": "cD0yMDI2LTA5...", "previous": null }
```

**Finite, user-sortable collections** (the menu) use **page** pagination:

```
GET /catalog/items/?limit=20&page=2&sort=price_asc
{ "results": [...], "next": "...?page=3", "previous": "...?page=1", "count": 47 }
```

> Cursor pagination cannot serve a sortable collection: it imposes its own
> `ordering` so the cursor stays monotonic, which silently overrides the
> caller's `sort`. Using it for the menu made every descending sort return
> ascending results.

### 0.4 Idempotency

`Idempotency-Key: <uuid4>` is **required** on `POST /orders/`, `POST /payments/initialise/`, `POST /reservations/`, `POST /academy/enrolments/`. Replaying a completed key returns the original response with `Idempotency-Replayed: true`.

### 0.5 Phase tags

🟢 Phase 1 · 🟡 Phase 2 · 🔵 Phase 3

---

## 1. Core / site  🟢

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/core/branch/` | — | Branch details, contact, coordinates, VAT policy, min order, free-delivery threshold |
| GET | `/core/opening-hours/` | — | Week schedule + `is_open_now` + `next_opens_at` |
| GET | `/core/settings/` | — | Social links, homepage stats, hero copy |
| GET | `/core/legal/` | — | ✅ index: slug, title, version, effective_from (no bodies) |
| GET | `/core/legal/{slug}/` | — | ✅ terms / privacy / cookies / refunds / accessibility |

`/core/legal/{slug}/` serves **the version in force today**: published, and with
`effective_from` on or before today. A draft or a future-dated version returns `404`
rather than leaking wording that does not yet apply. The response carries `version` and
`effective_from` so a client can show "last updated" honestly.

The index returns one row per slug, not one per version.

**`GET /core/branch/`**

```json
{
  "id": "…", "name": "Kuyash Place — Victoria Island", "slug": "vi",
  "phone": "+2348012345678", "email": "hello@kuyashplace.com",
  "address_line": "123 Gourmet Street, Victoria Island", "city": "Lagos", "state": "Lagos",
  "latitude": 6.4281, "longitude": 3.4219,
  "is_accepting_orders": true, "is_open_now": true,
  "prices_include_vat": true, "vat_rate_bps": 750,
  "min_order_value": { "amount": 200000, "currency": "NGN", "display": "₦2,000.00" },
  "free_delivery_threshold": { "amount": 1500000, "currency": "NGN", "display": "₦15,000.00" },
  "currency": "NGN", "timezone": "Africa/Lagos"
}
```

> `is_accepting_orders` and `is_open_now` are what the checkout button must respect. Today nothing stops a 3 a.m. order.

---

## 2. Catalogue  🟢

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/catalog/categories/` | — | Categories with item counts |
| GET | `/catalog/items/` | — | Menu list — filter/search/sort |
| GET | `/catalog/items/{slug}/` | — | Item detail with variants and modifier groups |
| GET | `/catalog/dietary-tags/` | — | Filter vocabulary |
| GET | `/catalog/featured/` | — | "What's Hot" |

**`GET /catalog/items/`** query parameters

| Param | Example | Notes |
|---|---|---|
| `category` | `burgers` | slug |
| `search` | `chicken` | name + description, Postgres full-text |
| `dietary` | `vegan,gluten-free` | AND semantics |
| `min_price` / `max_price` | `100000` | kobo |
| `min_rating` | `4` | **real**, from approved reviews |
| `available_only` | `true` | honours `is_available_now` + time windows |
| `sort` | `popular` | `popular` · `price_asc` · `price_desc` · `rating` · `newest` |

> All five sorts work server-side. `rating` and `newest` are currently `return 0` in `app/menu/page.tsx:104-106`.

**`GET /catalog/items/{slug}/`**

```json
{
  "id": "8f3c…", "slug": "signature-grill-plate",
  "name": "Signature Grill Plate",
  "description": "Slow-cooked beef with roasted garlic & herbs",
  "category": { "slug": "whats-hot", "name": "What's Hot", "emoji": "🔥" },
  "price": { "amount": 1490000, "currency": "NGN", "display": "₦14,900.00" },
  "compare_at_price": null,
  "images": [ { "url": "https://<ref>.supabase.co/storage/v1/object/public/kuyash-media/menu/sgp-card.webp",
                "alt_text": "Signature Grill Plate", "is_primary": true } ],
  "dietary_tags": [ { "slug": "halal", "name": "Halal", "icon": "…" } ],
  "allergen_note": "Contains garlic. Prepared in a kitchen handling nuts.",
  "calories": 780,
  "prep_time_minutes": 25,
  "average_rating": 4.6, "review_count": 38,
  "is_available_now": true,
  "variants": [
    { "id": "…", "name": "Regular", "price_delta": 0, "is_default": true },
    { "id": "…", "name": "Large",   "price_delta": 300000, "is_default": false }
  ],
  "modifier_groups": [
    { "id": "…", "name": "Add extras", "min_select": 0, "max_select": 3, "is_required": false,
      "modifiers": [
        { "id": "…", "name": "Extra sauce",  "price_delta": 50000,  "is_available": true },
        { "id": "…", "name": "Grilled plantain", "price_delta": 150000, "is_available": true }
      ] }
  ]
}
```

> Modifier groups are **per item**. The frontend currently renders one global `MOCK_CUSTOMIZATIONS` array on every dish, so pancakes are offered extra cheese — and the selections cost nothing.

---

## 3. Authentication and accounts  🟢

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/auth/csrf/` | — | Sets the CSRF cookie; call once on app load |
| POST | `/auth/register/` | — | Create account, send verification email |
| POST | `/auth/login/` | — | Establish session |
| POST | `/auth/logout/` | ✓ | Destroy session |
| GET | `/auth/session/` | — | Current user, or `{"user": null}` |
| POST | `/auth/verify-email/` | — | Confirm with emailed key |
| POST | `/auth/resend-verification/` | — | Rate-limited |
| POST | `/auth/password/reset/` | — | Send reset link |
| POST | `/auth/password/reset/confirm/` | — | uid + token + new password |
| POST | `/auth/password/change/` | ✓ | Requires current password |
| GET/PATCH | `/accounts/me/` | ✓ | Profile read/update |
| DELETE | `/accounts/me/` | ✓ | NDPR erasure — anonymises, retains financial records |
| GET/POST | `/accounts/addresses/` | ✓ | List / create |
| GET/PATCH/DELETE | `/accounts/addresses/{id}/` | ✓ | |
| POST | `/accounts/addresses/{id}/set-default/` | ✓ | |
| GET/PATCH | `/accounts/preferences/` | ✓ | 🟡 |
| GET | `/auth/social/google/` · `/facebook/` | — | 🟡 allauth redirect |

**`GET /auth/session/`** — the call that replaces "there is no concept of a logged-in user".

```json
{ "user": { "id": "…", "email": "ada@example.com", "full_name": "Ada Obi",
            "phone": "+2348012345678", "is_email_verified": true,
            "groups": ["customers"],
            "loyalty": { "points_balance": 1240, "tier": "Gold" } } }
```

**`POST /accounts/addresses/`** returns the resolved zone — the field that decides whether delivery is even possible:

```json
{ "id": "…", "label": "home", "recipient_name": "Ada Obi", "phone": "+2348012345678",
  "street": "12 Adeola Odeku Street", "city": "Lagos", "state": "Lagos",
  "landmark": "Opposite Eko Hotel", "delivery_notes": "Blue gate, call on arrival",
  "is_default": true,
  "zone": { "id": "…", "name": "Victoria Island",
            "fee": { "amount": 150000, "currency": "NGN", "display": "₦1,500.00" },
            "estimated_minutes": 35,
            "min_order_value": { "amount": 200000, "currency": "NGN", "display": "₦2,000.00" } } }
```

`"zone": null` ⇒ outside the delivery area. The UI must offer pickup instead of silently failing at checkout.

---

## 4. Cart  🟢

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/cart/` | optional | Current cart, **repriced on every read** |
| POST | `/cart/items/` | optional | Add a line |
| PATCH | `/cart/items/{id}/` | optional | Change quantity, instructions |
| DELETE | `/cart/items/{id}/` | optional | |
| DELETE | `/cart/` | optional | Empty |
| POST | `/cart/merge/` | ✓ | Fold the guest cart in after login |
| POST | `/cart/promo/` | optional | Apply a code |
| DELETE | `/cart/promo/` | optional | Remove |
| PATCH | `/cart/fulfilment/` | optional | Set delivery/pickup, address, tip |
| POST | `/cart/quote/` | — | ✅ Price a configured dish (size + options × quantity) without adding it. Same service the cart charges with; `is_available_now` is false outside a serving window |

Guests carry `X-Cart-Token` (issued on first write, echoed in `X-Cart-Token` response header).

**`POST /cart/items/`**

```json
{ "menu_item": "signature-grill-plate", "variant": "<uuid>", "quantity": 2,
  "modifiers": [ { "modifier": "<uuid>", "quantity": 1 } ],
  "special_instructions": "Less spicy" }
```

> No `price` field. If one is sent, it is ignored (CART-8).

**`GET /cart/`** — the authoritative totals response

```json
{
  "id": "…", "branch": "vi", "fulfilment_type": "delivery",
  "delivery_address": "<uuid>",
  "items": [
    { "id": "…", "menu_item": { "slug": "signature-grill-plate", "name": "Signature Grill Plate",
        "image_url": "https://…" },
      "variant_name": "Large", "quantity": 2,
      "modifiers": [ { "name": "Extra sauce", "price_delta": { "amount": 50000, "display": "₦500.00" } } ],
      "unit_price":    { "amount": 1840000, "currency": "NGN", "display": "₦18,400.00" },
      "line_subtotal": { "amount": 3680000, "currency": "NGN", "display": "₦36,800.00" },
      "special_instructions": "Less spicy", "is_available": true }
  ],
  "promo_code": "WELCOME10",
  "totals": {
    "subtotal":     { "amount": 3680000, "display": "₦36,800.00" },
    "discount":     { "amount": 368000,  "display": "₦3,680.00"  },
    "delivery_fee": { "amount": 0,       "display": "₦0.00"      },
    "vat":          { "amount": 231070,  "display": "₦2,310.70"  },
    "service_charge":{ "amount": 0,      "display": "₦0.00"      },
    "tip":          { "amount": 0,       "display": "₦0.00"      },
    "grand_total":  { "amount": 3312000, "display": "₦33,120.00" }
  },
  "vat_note": "VAT of ₦2,310.70 is included in the prices shown.",
  "delivery_note": "Free delivery applied — order over ₦15,000.00",
  "estimated_minutes": 55,
  "changes": [
    { "item": "chefs-special-pasta", "type": "price_increased",
      "old": { "display": "₦13,900.00" }, "new": { "display": "₦14,500.00" } }
  ],
  "unavailable": [
    { "item": "berry-cheesecake", "name": "Berry Cheesecake", "reason": "sold_out" }
  ],
  "can_checkout": false,
  "blockers": [ { "code": "item_unavailable", "detail": "Remove Berry Cheesecake to continue." } ]
}
```

**Everything the current cart computes in the browser is in `totals`.** The frontend deletes:

```tsx
const deliveryFee = appliedPromo?.type === "freeDelivery" ? 0 : subtotal > 0 ? 5.00 : 0;  // ❌
const tax = (subtotal - discount) * 0.075;                                                // ❌
const total = subtotal - discount + deliveryFee + tax;                                    // ❌
```

`changes[]` and `unavailable[]` solve a problem the current UI cannot even detect.

**`POST /cart/promo/`** `{ "code": "WELCOME10" }` → the repriced cart, or `422 promo_invalid` with a human-readable `detail`.

> There is deliberately **no endpoint that lists available promo codes.** The current cart UI enumerates them to the customer.

---

## 5. Orders  🟢

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/orders/` | optional | Place an order (Idempotency-Key required) |
| GET | `/orders/` | ✓ | Paginated history |
| GET | `/orders/{reference}/` | optional* | Detail + status. **Polling target.** ETag-cached |
| POST | `/orders/{reference}/cancel/` | optional* | Allowed while `paid` or `confirmed` |
| POST | `/orders/{reference}/reorder/` | ✓ | ✅ Rebuild a cart, revalidating price + availability |
| GET | `/orders/{reference}/receipt/` | optional* | ✅ PDF |

\* Guests authenticate by `reference` + the `guest_token` returned at creation.

**`GET /orders/mine/`** rows carry `preview`: the first two lines as
`{name, quantity, line_subtotal: Money, image_url}`, so a history card shows what was
ordered without a request per order.

**`GET /core/branch/`** carries `bank_transfer: {bank_name, account_name, account_number} | null`.
Null means transfer is switched off: the checkout hides it and `POST /orders/` refuses
`payment_method: "transfer"` with `409 checkout_blocked`.

**`POST /orders/{reference}/reorder/`**

Signed-in callers only, and only their own orders (404 otherwise — the existence
of a reference is not disclosed). A guest has no durable basket to rebuild into.

```json
{ "replace": false }
```

Answers `409 cart_not_empty` when the basket already has lines and `replace` is
false. Reorder discarding a basket the customer had already filled would be
destroying their work to save them a tap, so it takes an explicit confirmation.

```json
{
  "cart": { "…": "the full cart payload, repriced" },
  "added": 2,
  "replaced_lines": 0,
  "changes": [
    {
      "item": "classic-smash-burger",
      "name": "Classic Smash Burger",
      "type": "price_increased",
      "old": { "amount": 1090000, "display": "₦10,900.00" },
      "new": { "amount": 1290000, "display": "₦12,900.00" }
    }
  ],
  "unavailable": [
    { "item": "jollof-rice", "name": "Jollof Rice", "reason": "This dish is no longer on the menu." }
  ],
  "message": "Some items could not be added. Check your basket before paying."
}
```

A reorder is a **fresh quote**, not a copy. Lines come back at today's price and
any difference is reported; a delisted dish, a withdrawn size or a required
option with nothing left to choose is skipped and reported rather than
substituted. `changes[]` and `unavailable[]` use the same shape as the cart's,
so a client can render both with one component. `type` is one of
`price_increased`, `price_reduced`, `options_removed`.

Order lines hold the *name* of a variant and of each modifier, not a foreign
key — the snapshot has to outlive the catalogue row — so both are re-resolved by
name. A renamed option counts as a removed one, which is the safe direction: it
is reported rather than assumed equivalent.

**`GET /orders/{reference}/receipt/`**

`application/pdf`, `Content-Disposition: inline`. Answers `409 order_not_paid`
for an unpaid order: a document headed "Receipt" for money that was never
received causes the dispute it is meant to settle. A cash order becomes
receiptable when it is marked paid, not when it is placed.

Amounts are printed as `NGN 33,120.00`, not `₦33,120.00`. The standard PDF fonts
use WinAnsiEncoding, which has no U+20A6, and reportlab substitutes it silently
— a receipt reading `n33,120.00` is worse than one naming the currency. The JSON
API is unaffected and still returns `display` with the symbol.

The receipt prints the VAT rate and direction **snapshotted on the order**, not
today's branch settings: changing the branch must not rewrite a receipt that was
already issued.

**`POST /orders/`**

```http
POST /api/v1/orders/
Idempotency-Key: 4f1a...
```

```json
{
  "fulfilment_type": "delivery",
  "delivery_address": "<uuid>",
  "payment_method": "card",
  "payment_provider": "paystack",
  "tip": 100000,
  "customer_note": "Call when outside",
  "guest": { "email": "ada@example.com", "phone": "+2348012345678", "full_name": "Ada Obi" },
  "expected_total": 3312000
}
```

`expected_total` is the **price-changed guard**: if the server's recomputed total differs, the order is rejected with `409 price_changed` and the new totals, instead of silently charging a different amount.

**`201 Created`**

```json
{
  "reference": "KYS-7Q2XF9",
  "guest_token": "…",
  "status": "pending_payment",
  "payment": {
    "provider": "paystack",
    "authorization_url": "https://checkout.paystack.com/…",
    "reference": "KYS-7Q2XF9-1"
  },
  "totals": { "grand_total": { "amount": 3312000, "display": "₦33,120.00" } },
  "estimated_ready_at": "2026-09-11T19:05:00Z"
}
```

For `cash` and `transfer` the order is created `confirmed`/`pending_payment` with no `authorization_url`.

> The cart is **not** cleared here. It is cleared when payment is verified (`ORD-4`). The current frontend clears it before anything is persisted, making failure unrecoverable.

**`GET /orders/{reference}/`** — the polling endpoint

```json
{
  "reference": "KYS-7Q2XF9",
  "status": "preparing",
  "status_display": "Preparing your order",
  "payment_status": "paid",
  "fulfilment_type": "delivery",
  "placed_at": "2026-09-11T18:40:00Z",
  "estimated_delivery_at": "2026-09-11T19:25:00Z",
  "timeline": [
    { "status": "pending_payment",  "at": "2026-09-11T18:40:00Z", "reached": true },
    { "status": "paid",             "at": "2026-09-11T18:41:12Z", "reached": true },
    { "status": "confirmed",        "at": "2026-09-11T18:42:03Z", "reached": true },
    { "status": "preparing",        "at": "2026-09-11T18:43:30Z", "reached": true },
    { "status": "ready",            "at": null, "reached": false },
    { "status": "out_for_delivery", "at": null, "reached": false },
    { "status": "delivered",        "at": null, "reached": false }
  ],
  "items": [ { "name": "Signature Grill Plate", "variant_name": "Large", "quantity": 2,
               "modifiers": ["Extra sauce"], "special_instructions": "Less spicy",
               "unit_price": { "display": "₦18,400.00" },
               "line_subtotal": { "display": "₦36,800.00" },
               "image_url": "https://…" } ],
  "delivery_address": { "recipient_name": "Ada Obi", "phone": "+2348012345678",
                        "street": "12 Adeola Odeku Street", "city": "Lagos", "state": "Lagos",
                        "landmark": "Opposite Eko Hotel" },
  "rider": { "name": "Emeka", "phone": "+2348099887766" },
  "totals": { "...": "as in cart" },
  "can_cancel": false
}
```

Send `If-None-Match`; unchanged orders return `304` with no body. `timeline` is built from the append-only `OrderStatusEvent` log — the same structure the existing `OrderStatus.tsx` component already renders against mock data.

---

## 6. Payments  🟢

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/payments/initialise/` | optional | Start/retry a payment for an order |
| GET | `/payments/verify/{reference}/` | optional | Re-verify against the provider (called on redirect return) |
| POST | `/webhooks/paystack/` | — | Signature-verified, idempotent |
| POST | `/webhooks/flutterwave/` | — | Signature-verified, idempotent |
| GET | `/payments/methods/` | ✓ | 🟡 Saved cards (token + last4 only) |
| DELETE | `/payments/methods/{id}/` | ✓ | 🟡 |

> **There is no endpoint anywhere in this API that accepts a card number, expiry or CVV.** See [`PAYMENTS.md`](PAYMENTS.md).

**`GET /payments/verify/{reference}/`** — called when the browser returns from the provider. It is a *hint to re-verify*, never proof:

```json
{ "status": "success", "order_reference": "KYS-7Q2XF9", "order_status": "paid",
  "amount": { "amount": 3312000, "display": "₦33,120.00" } }
```

If the webhook already landed, this is a cheap confirmation. If it hasn't, this endpoint performs the verification itself. Either way the outcome is identical — **the result never depends on the client.**

---

## 7. Kitchen Display System (staff)  🟢

All require `kitchen`, `managers` or `admin` group membership.

| Method | Path | Purpose |
|---|---|---|
| GET | `/kds/orders/` | Live queue: `?status=confirmed,preparing,ready` |
| GET | `/kds/orders/{reference}/` | Full ticket with modifiers and instructions |
| POST | `/kds/orders/{reference}/accept/` | → `confirmed`; optional `prep_minutes` override |
| POST | `/kds/orders/{reference}/reject/` | → `rejected` + reason; **auto-refunds prepaid orders** |
| POST | `/kds/orders/{reference}/advance/` | `{ "to": "preparing" \| "ready" \| "out_for_delivery" \| "delivered" }` |
| POST | `/kds/orders/{reference}/assign-rider/` | `{ "rider": "<uuid>" }` |
| POST | `/kds/items/{slug}/availability/` | `{ "is_available_now": false }` — "86 this item" |
| GET | `/kds/summary/` | Counts by status, average prep time, today's revenue |
| GET | `/kds/reservations/today/` | 🟡 Today's book |

`GET /kds/orders/` returns `elapsed_seconds` and an `is_late` flag per order — the numbers a kitchen actually runs on.

---

## 8. Reservations  🟡

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/reservations/areas/` | — | Indoor / Outdoor / Private + surcharges |
| GET | `/reservations/availability/` | — | **Real** slots for `?date=&party_size=&area=` |
| POST | `/reservations/` | optional | Book (Idempotency-Key required) |
| GET | `/reservations/{reference}/` | optional* | |
| POST | `/reservations/{reference}/cancel/` | optional* | |
| PATCH | `/reservations/{reference}/` | optional* | Reschedule |
| GET | `/reservations/mine/` | ✓ | |

**`GET /reservations/availability/?date=2026-09-20&party_size=6&area=indoor`**

```json
{ "date": "2026-09-20", "party_size": 6,
  "slots": [
    { "time": "12:00", "available": true,  "tables_left": 3 },
    { "time": "12:30", "available": false, "reason": "fully_booked" },
    { "time": "19:00", "available": true,  "tables_left": 1 }
  ],
  "requires_manual_confirmation": false }
```

> The frontend currently hardcodes 18 slots from 11:00 to 22:00, all always available, because nothing can ever be booked.

---

## 9. Catering  🟡

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/catering/packages/` | — | Essential / Premium / Luxury |
| POST | `/catering/enquiries/` | optional | Submit — **persists and emails** |
| GET | `/catering/enquiries/{reference}/` | optional* | Status |

**`POST /catering/enquiries/`** accepts exactly the fields the existing form collects, plus returns what it currently cannot:

```json
{ "reference": "CAT-9K2M", "status": "new",
  "indicative_total": { "amount": 65000000, "display": "₦650,000.00" },
  "indicative_note": "Indicative only — a member of our team will confirm your quote.",
  "expected_response_by": "2026-09-12T18:40:00Z" }
```

> Replaces `alert("Thank you! We'll contact you within 24 hours…"); console.log(formData);`.

---

## 10. Support  🟡 / 🔵

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/support/contact/` | optional | 🟡 Persist + open a ticket |
| GET | `/support/faq/` | — | 🟡 Powers `/help` and the bot |
| GET | `/support/tickets/` · `/{ref}/` | ✓ | 🟡 |
| POST | `/support/tickets/{ref}/replies/` | ✓ | 🟡 |
| POST | `/support/chat/sessions/` | optional | ✅ Start. Returns `id`, the greeting and a `token` — send it as `X-Chat-Token` on every later call (a signed-in owner needs none). CSRF enforced for anonymous callers |
| GET | `/support/chat/sessions/{id}/` | token / owner | ✅ Reopen the transcript: `messages`, `is_ended`, `escalated_reference`. Anyone else gets 404 |
| POST | `/support/chat/sessions/{id}/messages/` | token / owner | ✅ `{body}` (≤ 500 chars) → `{message, reply}`. 409 `chat_ended` / `chat_expired` (12 h idle) → start again; 409 `chat_limit` (60 messages) → hand off |
| POST | `/support/chat/sessions/{id}/escalate/` | token / owner | ✅ `{name, email, message}` (name/email from the account when signed in) → `{reference, reply}`. Opens a ticket carrying the transcript, acknowledges the customer and alerts the team. Idempotent. Spam gets the same 201 with an empty reference |

**`POST /support/chat/sessions/{id}/messages/`**

```json
{ "message": { "sender": "user", "body": "Do you deliver to Ikoyi?", "created_at": "…",
               "suggestions": [], "can_escalate": false, "action": null },
  "reply":   { "sender": "bot",
               "body": "We deliver across Victoria Island, Ikoyi and Lekki Phase 1. …",
               "created_at": "…",
               "suggestions": ["How long does delivery take?", "Talk to a human"],
               "can_escalate": false,
               "action": null } }
```

The assistant (`apps/support/chat.py`, ADR-012) answers **only** from stored data, in this order:

1. **Order lookup** — a `KYS-XXXXXX` reference (dash optional), or "track my order". A signed-in owner gets the status, the stored estimate and a link to the order page. Anyone else must also give the email used on the order; a wrong email and a non-existent reference get the same reply, so references cannot be probed. Signed-in customers with nothing in progress are pointed to `/orders`.
2. **Handoff** — "human", "talk to", "complaint"… → `can_escalate: true` with no suggestions (the widget opens the form).
3. **Opening hours** — from `OpeningHours` and `HolidayOverride`: "open now until 22:00" or "open again tomorrow at 11:00".
4. **Greeting / thanks** — fixed text.
5. **FAQ** — three points per matching keyword phrase, one per shared question word, both sides lightly stemmed (so the keyword "delivery" matches "do you deliver"); an answer needs 3. The stored answer is returned verbatim, with up to two related questions as suggestions.
6. **Otherwise** — "I'd rather not guess", with a handoff offer. Never an invented answer.

Transcripts are in the admin (read-only), which is where to see what the FAQ fails to answer. A customer's chats are deleted on account erasure.

---

## 11. Reviews  🔵

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/reviews/?item={slug}` | — | ✅ Approved only, page-paginated with `count`. `?sort=newest\|helpful\|highest\|lowest`. Author shown as first name + last initial |
| POST | `/reviews/` | ✓ | ✅ `{order_line, rating, title, comment, recommends}`. `order_line` is `OrderDetail.items[].id` from a **delivered** order you own. 409 `review_not_allowed` (not delivered, dish removed) · 409 `already_reviewed` · 404 for a line that isn't yours |
| GET | `/reviews/{id}/` | ✓ author | ✅ Your review with `status`, `rejection_reason`, `can_edit`, `editable_until` |
| PATCH | `/reviews/{id}/` | ✓ author | ✅ Within `REVIEW_EDIT_WINDOW_DAYS` (default 7), else 409 `edit_window_closed`. An edit returns the review to `pending` |
| DELETE | `/reviews/{id}/` | ✓ author | ✅ At any time — a customer can always take down their own words. The window governs edits only |
| POST | `/reviews/{id}/helpful/` | optional | ✅ One vote per account or per client address (stored only as a salted hash). Returns `{helpful_count, counted}`. 409 `own_review`; 404 unless published. CSRF enforced for anonymous callers too |
| GET | `/reviews/pending/` | manager | ✅ Moderation queue, oldest first |
| POST | `/reviews/{id}/moderate/` | manager | ✅ `{action: approve\|reject, reason}`; `reason` required to reject and shown to the author. Reversible |

- Every review is a verified purchase: a review targets one order line (REV-5), and only lines of delivered orders qualify. "Delivered" means `delivered_at` is set — an order refunded after delivery stays reviewable, one refunded before it left does not.
- Order lines gained `id` (a UUID; the integer key never leaves the server), `review` (`{id, status, rating}` or null) and `can_review`.
- `MenuItem.average_rating` / `review_count` are rebuilt from approved reviews on every approval, rejection, edit and deletion (REV-4). Moderation happens here or in the Django admin; both go through the same service.
- On account erasure (`user_anonymised`) a person's reviews are deleted and the ratings they fed are recomputed.

---

## 12. Academy  🔵

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/academy/courses/` | — | ✅ Published courses, unpaginated. `?level=&type=&search=` (unknown level/type → 400). Each carries `price` (Money), `student_count` (computed), `instructor {name, photo_url}` and `next_cohort` (the soonest class with a free seat, else the soonest class, else null). No rating field |
| GET | `/academy/courses/{slug}/` | — | ✅ + instructor bio/specialities and upcoming `cohorts` |
| GET | `/academy/courses/{slug}/cohorts/` | — | ✅ Upcoming classes with `seats_left` |
| POST | `/academy/enrolments/` | optional | ✅ Idempotency-Key required; CSRF enforced. `{cohort, name, email, phone, experience_level, payment_method: card\|transfer, expected_amount}` → `{enrolment, payment: {reference, authorization_url} \| null, payment_error, guest_token?}`. 409 `cohort_full` · `cohort_unavailable` · `already_enrolled` · `transfer_unavailable` · `price_changed` |
| GET | `/academy/enrolments/mine/` | ✓ | ✅ |
| GET | `/academy/enrolments/{ref}/` | owner / `X-Enrolment-Token` / manager | ✅ Status, class, fee, `can_pay`, `bank_transfer` while unpaid, `certificate_available` |
| POST | `/academy/enrolments/{ref}/pay/` | owner / token | ✅ Start or retry the card payment. 409 `enrolment_not_payable` · `enrolment_expired` |
| GET | `/academy/payments/verify/{payment_ref}/` | — | ✅ Where the provider returns the student (`ACADEMY_PAYMENT_CALLBACK_URL`, default `/academy/enrolment/complete`). Asks the provider; `/payments/verify/` returns 404 for course payments |
| GET | `/academy/enrolments/{ref}/certificate/` | owner / token | ✅ PDF once issued; 409 `certificate_not_available` before |

- Seats are held on enrolment (card 30 min, transfer 48 h) and counted under a lock. Card fees go through the same payment providers and records as orders; transfers are confirmed by staff in the admin ("Record bank transfer received").
- Emails: `enrolment_confirmed` (ACA-7, with dates and schedule), `enrolment_transfer_details`, `enrolment_certificate`. Guests' links carry their token.
- Staff complete a student ("Mark completed and issue certificate") or cancel (any paid fee is refunded offline) in the admin.
- **No installments** (ACA-6): removed from the UI; OD-5 stays open.
- Seeded courses are **inactive** until staff confirm the instructor and fee and schedule a class.

---

## 13. Loyalty  🔵

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/loyalty/account/` | ✓ | ✅ `points_balance`, `lifetime_points`, `tier`, `next_tier {name, min_points, points_to_go}`, `progress_percent`, `earn_rate`, `applied_reward`, `birthday_on_file` |
| GET | `/loyalty/ledger/` | ✓ | ✅ Cursor-paginated, newest first |
| GET | `/loyalty/tiers/` | — | ✅ `{tiers: [{name, min_points, multiplier, earn_rate, birthday_points, benefits, colour}], base_earn_rate, expiry_inactive_days}` |
| GET | `/loyalty/rewards/` | — | ✅ Active catalogue. Public (the page markets it); `affordable` / `points_short` are null unless signed in |
| POST | `/loyalty/rewards/{id}/redeem/` | ✓ | ✅ Applies the reward to the active cart → Cart. 409 `insufficient_points` · `reward_unavailable` |
| DELETE | `/loyalty/rewards/applied/` | ✓ | ✅ Removes it → Cart |

- **Earning (LOY-2):** on `delivered`, `floor((subtotal − discounts) / LOYALTY_KOBO_PER_POINT) × tier multiplier`. Delivery, service charge and tips earn nothing. Guests earn nothing.
- **Spending (LOY-4):** a reward applied to the cart is priced like a promo code: the cart gains `promo_discount` and `loyalty_reward {id, name, points_cost, discount, free_delivery, applied, problem}`, and `totals.discount` is their sum. A reward whose conditions stop holding stays attached with a `problem` and takes nothing off. Points are spent inside `place_order`, re-checked under the account lock.
- **Reversal (LOY-5):** an order that ends `refunded`, `cancelled`, `rejected`, `expired` or `failed` has its earned points reversed and any spent reward points returned (stock restored). Partial refunds do not move points.
- **Birthdays (LOY-6):** daily task, once per member per year, at their tier's `birthday_points`; 29 February is celebrated on the 28th.
- **Expiry:** daily task; a positive balance with no earning or redemption for `LOYALTY_EXPIRY_INACTIVE_DAYS` (default 365) is expired.
- **Erasure:** the balance is expired and the account closed; the ledger stays.
- Seeded tiers keep the advertised thresholds and multipliers only. Seeded rewards are **inactive** until staff review them; the page's invented perks (concierge, catering discounts, referral and anniversary points) are not represented.

---

## 14. Gallery  🔵

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/gallery/` | — | ✅ Every published photo for the branch, in `display_order`. Not paginated (tens of photos; the page counts per category). `?category=food\|interior\|events\|team\|ambiance` (anything else → 400), `?tag={slug}`, `?featured=true` |
| GET | `/gallery/{id}/` | — | ✅ One photo + `previous_id` / `next_id`, following the same filters as the list; a photo outside the filter is 404 |

Photos are uploaded in the Django admin (branch preselected, thumbnails in the list, order/featured/visible editable inline). Uploads accept JPEG, PNG and WebP up to 10 MB; **SVG is refused** because files are served from a public bucket and SVG can carry script. `alt_text` falls back to the title.

---

## 15. Wishlist  🟡

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/wishlist/` | ✓ | |
| POST | `/wishlist/` | ✓ | `{ "menu_item": "slug" }` |
| DELETE | `/wishlist/{item_slug}/` | ✓ | |
| POST | `/wishlist/sync/` | ✓ | Merge the localStorage wishlist on first login |

---

## 16. Rate limits

| Scope | Limit |
|---|---|
| Anonymous, global | 100/min per IP |
| Authenticated, global | 300/min per user |
| `POST /auth/login/` | 5/min per IP **and** 10/hour per email |
| `POST /auth/register/` | 3/hour per IP |
| `POST /auth/password/reset/` | 3/hour per email |
| `POST /orders/` | 10/hour per user or IP |
| `POST /cart/promo/` | 10/min per cart — **stops promo-code brute force** |
| `POST /support/contact/` | 3/hour per IP |
| `POST /catering/enquiries/` | 5/hour per IP |
| `POST /reviews/` | 10/hour per user |
| `POST /reviews/{id}/helpful/` | 60/hour per user or IP |
| `POST /support/chat/sessions/` | 20/hour per user or IP |
| `POST /support/chat/sessions/{id}/messages/` | 30/min per user or IP |
| `POST /support/chat/sessions/{id}/escalate/` | 3/hour per user or IP |
| `POST /academy/enrolments/` | 10/hour per user or IP |
| `POST /loyalty/rewards/{id}/redeem/` | global user rate (sign-in required; nothing to brute-force) |
| Webhooks | unlimited, signature-gated |

429 responses carry `Retry-After`.

Scoped limits count **writes only** (`apps/common/throttling.py`): reading `/orders/` history does not use up the allowance for placing an order. Until Phase 3.1 the scoped rows above were declared but never enforced — no view installed `ScopedRateThrottle` — so they fell back to the global limit; `apps/common/tests/test_scoped_throttles.py` now fails if a view declares a scope without the throttle.

---

## 17. Endpoints the frontend needs that do not exist yet

Checklist for the integration PR. Each currently has a hardcoded or faked counterpart:

| Frontend need | Endpoint | Replaces |
|---|---|---|
| "Am I logged in?" | `GET /auth/session/` | nothing — no such concept exists |
| Menu | `GET /catalog/items/` | `lib/data/menu.ts` |
| Item images | image URLs in the payload | `lib/assets/images.ts` |
| Cart totals | `GET /cart/` | `CartSummary.tsx:21-24` |
| Promo validation | `POST /cart/promo/` | `lib/store/promoStore.ts` |
| Place order | `POST /orders/` | `app/checkout/page.tsx:44` |
| Pay | `POST /payments/initialise/` | `PaymentStep.tsx` card fields |
| Track order | `GET /orders/{ref}/` | `app/orders/[id]/page.tsx:38` |
| Order history | `GET /orders/` | `orderHistoryStore` (never written) |
| Profile | `GET/PATCH /accounts/me/` | `ProfileSection.tsx:9` |
| Addresses | `/accounts/addresses/` | `AddressesSection.tsx:18` |
| Saved cards | `GET /payments/methods/` | `PaymentMethodsSection.tsx:16` |
| Reservation slots | `GET /reservations/availability/` | 18 hardcoded slots |
| Book a table | `POST /reservations/` | `alert("Reservation submitted!")` |
| Catering quote | `POST /catering/enquiries/` | `console.log` |
| Contact | `POST /support/contact/` | local state only |
| Review | `POST /reviews/` | `alert()` + `console.log` |
| Courses | `GET /academy/courses/` | `COURSES` array inside the page file |
| Enrol | `POST /academy/enrolments/` | `alert()` |
| Rewards | `GET /loyalty/account/` | `useState(false)` |
| Gallery | `GET /gallery/` | 20 items with broken image keys |
| Chat | `/support/chat/…` | local echo |
| Opening hours | `GET /core/opening-hours/` | hardcoded footer text |
