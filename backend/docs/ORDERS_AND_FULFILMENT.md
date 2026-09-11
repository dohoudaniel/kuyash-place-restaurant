# Orders & Fulfilment

The order state machine, the Kitchen Display System, delivery zones and riders.

---

## 1. Order state machine

```
                      ┌──────────────────┐
                      │ pending_payment  │  card/transfer: awaiting money
                      └────────┬─────────┘
                 ┌─────────────┼──────────────┐
        payment  │             │ timeout 30m  │ customer cancels
        verified ▼             ▼              ▼
              ┌──────┐   ┌──────────┐   ┌───────────┐
              │ paid │   │ expired  │   │ cancelled │
              └──┬───┘   └──────────┘   └───────────┘
    kitchen      │        kitchen rejects
    accepts      │              │
                 ▼              ▼
          ┌───────────┐   ┌──────────┐
          │ confirmed │   │ rejected │──▶ auto-refund if prepaid
          └─────┬─────┘   └──────────┘
                │ COD orders enter here directly
                ▼
          ┌───────────┐
          │ preparing │
          └─────┬─────┘
                ▼
          ┌───────────┐
          │   ready   │
          └─────┬─────┘
        ┌───────┴────────┐
   delivery          pickup
        ▼                ▼
┌──────────────────┐     │
│ out_for_delivery │     │
└────────┬─────────┘     │
         └───────┬───────┘
                 ▼
          ┌────────────┐
          │ delivered  │ ──▶ loyalty points awarded
          └─────┬──────┘
                │ staff/admin only
                ▼
          ┌────────────┐
          │  refunded  │
          └────────────┘
```

### 1.1 Legal transitions

```python
TRANSITIONS: dict[str, set[str]] = {
    "pending_payment":  {"paid", "cancelled", "expired", "failed"},
    "paid":             {"confirmed", "rejected", "cancelled", "refunded"},
    "confirmed":        {"preparing", "cancelled", "refunded"},
    "preparing":        {"ready", "cancelled", "refunded"},
    "ready":            {"out_for_delivery", "delivered", "refunded"},
    "out_for_delivery": {"delivered", "failed_delivery"},
    "delivered":        {"refunded"},
    "failed_delivery":  {"out_for_delivery", "cancelled", "refunded"},
    "rejected":         {"refunded"},
    "cancelled":        {"refunded"},
    "expired":          set(),
    "refunded":         set(),
    "failed":           set(),
}
```

### 1.2 Who may trigger what

| Transition | Customer | Kitchen | Rider | Manager | System |
|---|:--:|:--:|:--:|:--:|:--:|
| → `paid` | | | | | ✓ webhook |
| → `confirmed` | | ✓ | | ✓ | ✓ COD auto |
| → `rejected` | | ✓ | | ✓ | |
| → `preparing` | | ✓ | | ✓ | |
| → `ready` | | ✓ | | ✓ | |
| → `out_for_delivery` | | ✓ | ✓ | ✓ | |
| → `delivered` | | | ✓ | ✓ | |
| → `cancelled` | ✓ * | | | ✓ | ✓ timeout |
| → `refunded` | | | | ✓ ** | ✓ on reject |

\* Customers may cancel only while `paid` or `confirmed` (ORD-10).
\*\* Up to the manager refund ceiling; above it, admin only.

### 1.3 The transition service

Every state change goes through one function. There is no other way to mutate `Order.status`.

```python
# apps/orders/services/state.py
def transition(order: Order, to: str, *, actor=None, source="system", note="") -> Order:
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)

        if to not in TRANSITIONS[order.status]:
            raise IllegalTransition(f"{order.status} → {to} is not permitted")
        if actor and not can_transition(actor, order, to):
            raise PermissionDenied(...)

        frm, order.status = order.status, to
        _stamp_timestamp(order, to)                 # accepted_at, ready_at, delivered_at…
        order.save(update_fields=["status", *_TIMESTAMP_FIELDS[to], "updated_at"])

        OrderStatusEvent.objects.create(            # append-only audit (ORD-8)
            order=order, from_status=frm, to_status=to,
            actor=actor, actor_role=_role_of(actor), source=source, note=note,
        )
        order_status_changed.send(Order, order=order, from_status=frm, to_status=to)
    return order
```

`select_for_update()` is what prevents two staff members double-advancing the same ticket during a rush.

### 1.4 Side effects, by signal

| Event | Listener | Action |
|---|---|---|
| → `paid` | `carts` | Clear the cart — **now**, not at submit (ORD-4) |
| → `paid` | `notifications` | Order confirmation email |
| → `paid` | `promotions` | `PromoRedemption` pending → confirmed |
| → `confirmed` | `notifications` | "Your order is confirmed", with ETA |
| → `out_for_delivery` | `notifications` | "On the way", with rider name and phone |
| → `delivered` | `loyalty` | Award points (LOY-2) |
| → `delivered` | `catalog` | Increment `order_count` for popularity sorting |
| → `delivered` | `reviews` | Unlock review eligibility for those lines |
| → `rejected` | `payments` | Auto-refund if prepaid (RF-5) |
| → `refunded` | `loyalty` | Reverse points (LOY-5) |
| → `refunded` | `promotions` | Reverse the redemption (RF-4) |

---

## 2. Order reference generation

```python
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"      # no 0/O/1/I — read aloud on the phone

def generate_reference() -> str:
    for _ in range(10):
        ref = "KYS-" + "".join(secrets.choice(ALPHABET) for _ in range(6))
        if not Order.objects.filter(reference=ref).exists():
            return ref
    raise RuntimeError("reference space exhausted")
```

32⁶ ≈ 1.07 billion values. Contrast with the current `KYS-${Date.now().toString(36).toUpperCase()}`, which is client-generated, sequential, collision-prone between concurrent users and leaks order timing.

---

## 3. ETA calculation

Replaces the hardcoded "30–45 mins" copy with something derived from reality.

```python
def estimate(order: Order) -> tuple[datetime, datetime | None]:
    base = max((i.menu_item.prep_time_minutes or branch.default_prep_minutes)
               for i in order.items.all())
    volume = sum(i.quantity for i in order.items.all())
    base += (volume // 5) * 3                                  # batching penalty

    active = Order.objects.filter(branch=order.branch,
                                  status__in=["confirmed", "preparing"]).count()
    load_factor = 1 + min(active / 10, 1.0)                    # capped at 2×
    prep = int(base * load_factor)

    ready_at = timezone.now() + timedelta(minutes=prep)
    if order.fulfilment_type == "pickup":
        return ready_at, None
    return ready_at, ready_at + timedelta(minutes=order.zone_estimated_minutes)
```

Kitchen staff may override `prep_minutes` when accepting an order — they know when the fryer is backed up and the model does not.

---

## 4. Kitchen Display System

### 4.1 What it is

One screen the kitchen keeps open, polling `GET /api/v1/kds/orders/` every 10 seconds (WebSockets in Phase 3). Not the Django admin — admin is for content and pricing; the KDS is for service.

### 4.2 Ticket payload

```json
{
  "reference": "KYS-7Q2XF9",
  "status": "confirmed",
  "placed_at": "2026-09-11T18:40:00Z",
  "elapsed_seconds": 412,
  "is_late": false,
  "fulfilment_type": "delivery",
  "zone": "Victoria Island",
  "payment_status": "paid",
  "payment_method": "card",
  "items": [
    { "quantity": 2, "name": "Signature Grill Plate", "variant": "Large",
      "modifiers": ["Extra sauce", "Grilled plantain"],
      "special_instructions": "Less spicy" }
  ],
  "customer_note": "Call when outside",
  "customer": { "name": "Ada Obi", "phone": "+2348012345678" },
  "grand_total": { "display": "₦33,120.00" }
}
```

> `modifiers` and `special_instructions` are rendered **most prominently** (KDS-5). They are what the kitchen actually cooks from, and they are exactly the fields the current frontend collects and then discards.

### 4.3 Operational requirements

| ID | Requirement |
|---|---|
| KDS-A | Tickets sorted oldest-first with a visible elapsed timer |
| KDS-B | `is_late` (elapsed > ETA) renders red |
| KDS-C | One tap per transition; no free-text state editing |
| KDS-D | Reject requires a reason from a fixed list |
| KDS-E | "86 this item" is reachable in two taps and applies instantly to the public menu |
| KDS-F | Unpaid COD tickets are visually distinct — the rider must collect |
| KDS-G | Audible alert on a new ticket |
| KDS-H | Degrades safely on connection loss: shows last-known state with a stale banner, never a blank screen |
| KDS-I | Every action attributed to the acting staff user |

### 4.4 "86 this item"

```
POST /api/v1/kds/items/signature-grill-plate/availability/
{ "is_available_now": false, "reason": "sold_out" }
```

Effects, immediately: hidden from the public catalogue; flagged in every active cart via `unavailable[]`; blocks checkout for affected carts with an actionable message. Auto-resets at the next service period unless pinned.

---

## 5. Delivery

### 5.1 Zones

Replaces the flat `₦5.00` hardcoded in two cart components.

| Zone | Fee | Min order | ETA |
|---|---|---|---|
| Victoria Island | ₦1,500 | ₦2,000 | 35 min |
| Ikoyi | ₦1,800 | ₦2,000 | 40 min |
| Lekki Phase 1 | ₦2,500 | ₦3,000 | 50 min |

*Placeholder values — the owner sets real ones in admin before launch.*

### 5.2 Resolution

Phase 1 is string matching on `city`/`area` against each zone's `areas` list, with a manual zone override in the address form. Phase 3 upgrades to GeoJSON polygon containment via PostGIS.

An address that resolves to no zone returns `zone: null`, and the UI must offer **pickup** rather than letting the customer reach checkout and fail (`422 outside_delivery_area`).

### 5.3 Free delivery

Applied server-side when any of: order subtotal ≥ `Branch.free_delivery_threshold`; an active `free_delivery` promo; or a loyalty reward redemption. The `delivery_note` string in the cart response explains which — so the UI never has to guess why the fee vanished.

### 5.4 Riders

```
ready → assign-rider → out_for_delivery → delivered
```

`DeliveryAssignment` records `assigned_at`, `picked_up_at`, `delivered_at` and `cash_collected`. A rider sees only their own assignments. Shift-end reconciliation compares `cash_collected` against the sum of COD order totals and flags shortfalls.

---

## 6. Order lifecycle timings

| Rule | Value |
|---|---|
| `pending_payment` expiry | 30 minutes → `expired`, cart contents restored |
| Customer cancellation window | Until `preparing` |
| Kitchen accept SLA | 5 minutes; overdue tickets escalate visually |
| Review eligibility | Opens at `delivered`, closes after 30 days |
| Guest order token validity | 30 days |
| Order retention | 7 years (tax records); personal data anonymised on account deletion |

---

## 7. Reordering  *(Phase 2)*

```
POST /orders/KYS-7Q2XF9/reorder/
```

Server-side, because prices and availability move:

1. Load the historical order's items
2. Match each `menu_item` FK to the live catalogue
3. Drop items that are deleted or unavailable → report in `removed[]`
4. Reprice everything at current prices → report in `repriced[]`
5. Build a fresh cart and return it

```json
{ "cart": { "...": "..." },
  "removed":  [ { "name": "Berry Cheesecake", "reason": "no_longer_available" } ],
  "repriced": [ { "name": "Classic Smash Burger",
                  "old": { "display": "₦10,900.00" },
                  "new": { "display": "₦11,500.00" } } ] }
```

> The current `/orders` page does this client-side by clearing the cart and re-adding items at **historical prices**, from a store nothing ever writes to. It would sell at last year's prices if it worked at all.

---

## 8. Failure modes and their handling

| Failure | Handling |
|---|---|
| Payment webhook never arrives | `verify_pending_payments` beat task settles it within 10 min |
| Customer pays, item sold out meanwhile | Kitchen rejects → auto-refund + apology email |
| Rider marks delivered, customer disputes | `OrderStatusEvent` log shows actor and timestamp |
| Kitchen accepts twice concurrently | `select_for_update` + transition guard; second attempt gets `409` |
| Customer double-taps "Confirm Order" | `Idempotency-Key` returns the first response |
| Branch closes mid-checkout | Order placement rejected with `409 branch_closed` |
| Price changes mid-checkout | `409 price_changed` with new totals; customer re-confirms |
| Promo exhausted mid-checkout | `422 promo_invalid`; order placeable without it |
| Provider outage on initialise | Automatic fallback to the secondary provider |
| Order stuck in `preparing` overnight | Daily stale-order report to managers |
