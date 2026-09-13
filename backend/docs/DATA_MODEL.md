# Data Model — Kuyash Place Backend

Every model, field, constraint and index. Phase tags mark when each lands.

**Universal conventions**

- `id` — `UUIDField(primary_key=True, default=uuid4, editable=False)` on every model
- `created_at` / `updated_at` — on every model via `TimeStampedModel`
- **All money fields are `PositiveBigIntegerField` storing integer kobo.** ₦1,250.00 → `125000`. Never `Decimal`, never `Float`, never a string.
- All enums are `models.TextChoices`
- All timestamps stored UTC; business-hours logic uses `Africa/Lagos`

---

## 1. `common` — shared base classes

```python
class TimeStampedModel(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class SoftDeleteModel(models.Model):
    is_active  = models.BooleanField(default=True, db_index=True)
    class Meta: abstract = True
```

`MoneyField` is a thin `PositiveBigIntegerField` subclass carrying `help_text="Amount in kobo (₦1.00 = 100)"` so no admin user ever types naira into it by mistake.

---

## 2. `core` — branch and site configuration  *(Phase 1)*

### Branch

One row today; the FK target that makes a second outlet a data change rather than a rewrite.

| Field | Type | Notes |
|---|---|---|
| `name` | `CharField(120)` | "Kuyash Place — Victoria Island" |
| `slug` | `SlugField(unique=True)` | |
| `phone` / `whatsapp` / `email` | `CharField` / `EmailField` | |
| `address_line` / `city` / `state` | `CharField` | |
| `latitude` / `longitude` | `DecimalField(9,6)` null | for the map section |
| `timezone` | `CharField(64)` | default `"Africa/Lagos"` |
| `currency` | `CharField(3)` | default `"NGN"` |
| **`prices_include_vat`** | `BooleanField` | **default `True`.** Governs VAT direction — see `PRD.md` §7 |
| `vat_rate_bps` | `PositiveIntegerField` | basis points; default `750` = 7.5%. Integer, so no float rate |
| `service_charge_bps` | `PositiveIntegerField` | default `0` |
| `is_accepting_orders` | `BooleanField` | manual kill switch for a slammed kitchen |
| `min_order_value` | Money | |
| `free_delivery_threshold` | Money null | null = no free-delivery threshold |
| `default_prep_minutes` | `PositiveIntegerField` | fallback when items have none |
| `is_active` | `BooleanField` | |

### OpeningHours

| Field | Type | Notes |
|---|---|---|
| `branch` | FK → Branch | `related_name="opening_hours"` |
| `weekday` | `PositiveSmallIntegerField` | 0=Mon … 6=Sun |
| `opens_at` / `closes_at` | `TimeField` | |
| `service` | `CharField` choices | `all_day` / `breakfast` / `lunch` / `dinner` — supports split services |
| `is_closed` | `BooleanField` | |

`UniqueConstraint(branch, weekday, service)`.

### HolidayOverride

`branch`, `date`, `is_closed`, `opens_at` null, `closes_at` null, `note`. Wins over `OpeningHours`.

### SiteSettings *(singleton)*

Social links, hero copy, homepage statistics (currently hardcoded in the frontend), contact emails, map embed. One row, enforced by `save()`.

### LegalPage  *(Phase 2.6 — delivered)*

| Field | Type | Notes |
|---|---|---|
| `slug` | `SlugField` | `terms`, `privacy`, `cookies`, `refunds`, `accessibility` — **not unique on its own** |
| `version` | `PositiveIntegerField` | unique together with `slug` |
| `title` | `CharField(200)` | |
| `body` | `TextField` | markdown |
| `summary` | `CharField(300)` | what changed in this version |
| `effective_from` | `DateField` | a future date is a *scheduled* change, not the current policy |
| `published` | `BooleanField` | drafts are invisible to customers and to the API |

Constraint: `unique_legal_page_version` on `(slug, version)`.

**Versions are retained, not overwritten.** `slug` is deliberately not unique: which
wording a customer agreed to matters if it is ever disputed, so a change is a new row
and the old one stays readable. In the admin, a published version is read-only except
for `published` itself — you withdraw a page by unpublishing it, and change it with the
*Draft a new version* action. `LegalPage.current(slug)` resolves the wording in force
today, ignoring drafts and future-dated versions.

> Replaces five hardcoded route files, **and is where the tax-copy contradiction gets fixed** (`app/help/page.tsx:120` and `app/terms/page.tsx:47` claim tax-inclusive pricing while the cart adds 7.5% on top).
>
> The fix is structural, not editorial. The pricing sentence in the seeded terms is
> *generated* from `Branch.prices_include_vat` (`apps/core/legal_seed.py`), and
> `manage.py check --deploy` fails with **`kuyash.E002`** if any published page asserts a
> VAT direction the branch does not charge. The check looks for the *opposing* claim
> rather than for exact seeded wording, so staff can reword the pages freely — only a
> contradiction fails the build. `kuyash.W003` warns when `terms`, `privacy` or `refunds`
> has no published version at all.

---

## 3. `accounts`  *(Phase 1)*

### User

Custom user, `AbstractBaseUser` + `PermissionsMixin`, **email as `USERNAME_FIELD`** (the frontend has no username field anywhere).

| Field | Type | Notes |
|---|---|---|
| `email` | `EmailField(unique=True)` | login identity |
| `phone` | `CharField(20)` | E.164; required for delivery contact |
| `full_name` | `CharField(150)` | the UI collects one name field, not first/last |
| `is_email_verified` | `BooleanField` | managed by allauth |
| `is_staff` / `is_active` / `is_superuser` | `BooleanField` | |
| `date_joined` / `last_login` | `DateTimeField` | |

Roles are Django `Group`s: `customers`, `kitchen`, `riders`, `managers`. No `role` column.

### Profile

`user` (O2O), `date_of_birth` null (drives birthday rewards), `avatar` (Supabase), `marketing_opt_in`, `dietary_preferences` (M2M → `catalog.DietaryTag`), `default_address` (FK → Address null), `preferred_language`.

### Address

Replaces `AddressesSection.tsx`'s hardcoded two-entry array.

| Field | Type | Notes |
|---|---|---|
| `user` | FK → User | `related_name="addresses"` |
| `label` | choices | `home` / `work` / `other` |
| `recipient_name` | `CharField(150)` | |
| `phone` | `CharField(20)` | |
| `street` | `CharField(255)` | |
| `city` / `state` | `CharField` | |
| `landmark` | `CharField(255)` blank | essential in Lagos; the current form has no such field |
| `delivery_notes` | `TextField` blank | "Ring doorbell twice" |
| `zone` | FK → `delivery.DeliveryZone` null | resolved on save; null = outside delivery area |
| `latitude` / `longitude` | `DecimalField` null | |
| `is_default` | `BooleanField` | partial unique index: one default per user |

```python
UniqueConstraint(fields=["user"], condition=Q(is_default=True), name="one_default_address_per_user")
```

---

## 4. `catalog`  *(Phase 1)*

Replaces `frontend/lib/data/menu.ts` and `frontend/lib/assets/images.ts` entirely.

### Category

`branch` FK, `name`, `slug` (unique per branch), `emoji` (the UI uses 🔥🍔🍗🌮🥞🍰), `description`, `display_order`, `image`, `is_active`.

### DietaryTag

`name`, `slug`, `icon`. Seeded: vegetarian, vegan, gluten-free, contains-nuts, contains-dairy, halal, spicy, chef-special.

> **This makes the dietary filter real.** It is currently `// Mock: would filter based on item dietary properties` at `app/menu/page.tsx:87`.

### MenuItem

| Field | Type | Notes |
|---|---|---|
| `branch` | FK → Branch | |
| `category` | FK → Category | `related_name="items"` |
| `name` | `CharField(150)` | |
| `slug` | `SlugField` | **the stable public ID** — replaces `imageKey \|\| slugify(name)` |
| `description` | `TextField` | |
| `base_price` | Money | kobo |
| `compare_at_price` | Money null | for "was ₦X" strike-throughs |
| **`needs_repricing`** | `BooleanField` | **default `True` on seed.** Admin shows a blocking banner until cleared |
| `tax_class` | choices | `standard` / `zero_rated` / `exempt` |
| `prep_time_minutes` | `PositiveSmallIntegerField` | feeds the order ETA; replaces hardcoded "30–45 mins" |
| `calories` | `PositiveIntegerField` null | |
| `allergen_note` | `CharField(255)` blank | |
| `dietary_tags` | M2M → DietaryTag | |
| `is_active` | `BooleanField` | permanently listed or not |
| `is_available_now` | `BooleanField` | the KDS "86 this item" toggle |
| `is_featured` | `BooleanField` | drives "What's Hot" |
| `display_order` | `PositiveIntegerField` | |
| `average_rating` | `DecimalField(2,1)` | **denormalised from approved reviews.** Replaces the literal `5.0` on every card |
| `review_count` | `PositiveIntegerField` | |
| `order_count` | `PositiveIntegerField` | denormalised; powers real "sort by popular" |
| `published_at` | `DateTimeField` null | powers real "sort by newest" — currently `return 0` |

Indexes: `(branch, category, is_active, display_order)`, `(branch, is_featured)`, GIN on `name`/`description` for search.

### MenuItemImage

`item` FK, `image` (Supabase), `alt_text`, `display_order`, `is_primary`.

> Retires `lib/assets/images.ts`. Note that 20 gallery entries and several menu entries currently reference image keys with no corresponding file.

### AvailabilityWindow

`item` FK, `weekday`, `starts_at`, `ends_at`. Empty set = always available. Makes breakfast items actually breakfast-only.

### Variant

| Field | Type | Notes |
|---|---|---|
| `item` | FK → MenuItem | `related_name="variants"` |
| `name` | `CharField(80)` | "Regular", "Large", "Family" |
| `price_delta` | `BigIntegerField` | signed kobo — may be negative |
| `is_default` | `BooleanField` | |
| `display_order` / `is_active` | | |

### ModifierGroup

Replaces the global `MOCK_CUSTOMIZATIONS` array that currently offers extra cheese on pancakes.

| Field | Type | Notes |
|---|---|---|
| `item` | FK → MenuItem | `related_name="modifier_groups"` — **per item**, not global |
| `name` | `CharField(120)` | "Choose your protein", "Add extras" |
| `min_select` | `PositiveSmallIntegerField` | `0` = optional |
| `max_select` | `PositiveSmallIntegerField` | `1` = radio, `>1` = checkboxes |
| `is_required` | `BooleanField` | |
| `display_order` | | |

`CheckConstraint(min_select <= max_select)`.

### Modifier

`group` FK, `name`, `price_delta` (signed kobo — **this is what makes a protein upgrade actually cost money**), `is_default`, `is_available`, `display_order`.

---

## 5. `delivery`  *(Phase 1)*

### DeliveryZone

| Field | Type | Notes |
|---|---|---|
| `branch` | FK → Branch | |
| `name` | `CharField(120)` | "Victoria Island", "Lekki Phase 1" |
| `fee` | Money | flat, kobo — replaces the hardcoded `₦5.00` |
| `min_order_value` | Money | |
| `estimated_minutes` | `PositiveSmallIntegerField` | feeds the ETA |
| `polygon` | `TextField` null | GeoJSON; Phase 3 for automatic resolution |
| `postcodes` / `areas` | `JSONField` | string matching for Phase 1 resolution |
| `is_active` | `BooleanField` | |

### RiderProfile

`user` O2O, `phone`, `vehicle_type` (`bike`/`car`/`foot`), `is_on_shift`, `current_zone` FK null.

### DeliveryAssignment

`order` O2O, `rider` FK, `assigned_at`, `picked_up_at` null, `delivered_at` null, `cash_collected` Money null (COD reconciliation), `notes`.

---

## 6. `carts`  *(Phase 1)*

### Cart

| Field | Type | Notes |
|---|---|---|
| `user` | FK → User null | null for guests |
| `session_token` | `CharField(64)` indexed | anonymous cart identity |
| `branch` | FK → Branch | |
| `status` | choices | `active` / `converted` / `abandoned` |
| `promo_code` | FK → PromoCode null | applied, not yet redeemed |
| `tip` | Money | default 0 |
| `fulfilment_type` | choices | `delivery` / `pickup` |
| `delivery_address` | FK → Address null | |
| `expires_at` | `DateTimeField` | |

`UniqueConstraint(user, branch, condition=Q(status="active"))` — one live cart per user per branch.

### CartItem

| Field | Type | Notes |
|---|---|---|
| `cart` | FK → Cart | |
| `menu_item` | FK → MenuItem | **FK, not a string ID** (CART-3) |
| `variant` | FK → Variant null | |
| `quantity` | `PositiveSmallIntegerField` | `CheckConstraint(quantity > 0)` |
| `special_instructions` | `TextField` blank | |
| `unit_price_snapshot` | Money | price when added — enables change detection |

### CartItemModifier

`cart_item` FK, `modifier` FK, `quantity`. The join that makes modifiers priceable.

> **Cart totals are not stored.** They are computed on every read by `carts/services/pricing.py`, which is what guarantees a stale cart cannot lock in a stale price.

---

## 7. `promotions`  *(Phase 1)*

### PromoCode

Replaces `lib/store/promoStore.ts`, which currently ships every code and its rules to the browser.

| Field | Type | Notes |
|---|---|---|
| `branch` | FK → Branch | |
| `code` | `CharField(32)` uppercase, unique per branch | |
| `description` | `CharField(255)` | |
| `discount_type` | choices | `percentage` / `fixed` / `free_delivery` |
| `value` | `PositiveIntegerField` | basis points for percentage, kobo for fixed |
| `min_order_value` | Money | |
| `max_discount` | Money null | caps a percentage discount |
| `valid_from` / `valid_until` | `DateTimeField` | |
| `usage_limit` | `PositiveIntegerField` null | total across all customers |
| `usage_limit_per_user` | `PositiveIntegerField` null | |
| `used_count` | `PositiveIntegerField` | denormalised from the ledger |
| `first_order_only` | `BooleanField` | |
| `applicable_categories` | M2M → Category blank | empty = everything |
| `applicable_items` | M2M → MenuItem blank | |
| `is_active` | `BooleanField` | |
| `is_public` | `BooleanField` | **default `False`** — governs whether it may ever be listed. The current UI lists all codes to the user |

### PromoRedemption

`promo_code` FK, `user` FK null, `order` FK, `discount_amount` Money, `status` (`pending`/`confirmed`/`reversed`), `redeemed_at`.

`UniqueConstraint(promo_code, order)`. This ledger is what makes `usage_limit` enforceable and reversible on refund — the current `usedCount` field is decorative and resets on page refresh.

---

## 8. `orders`  *(Phase 1)*

### Order

| Field | Type | Notes |
|---|---|---|
| `reference` | `CharField(20) unique` | `KYS-` + 6 random base32 chars. **Server-generated, non-sequential.** Replaces `KYS-${Date.now().toString(36)}` |
| `branch` | FK → Branch | |
| `user` | FK → User null | null = guest checkout |
| `guest_email` / `guest_phone` | `EmailField` / `CharField` | required when `user` is null |
| `status` | choices | see `ORDERS_AND_FULFILMENT.md` |
| `fulfilment_type` | choices | `delivery` / `pickup` |
| `payment_method` | choices | `card` / `transfer` / `cash` |
| `payment_status` | choices | `unpaid` / `pending` / `paid` / `partially_refunded` / `refunded` / `failed` |
| **Address snapshot** | | `recipient_name`, `phone`, `street`, `city`, `state`, `landmark`, `delivery_notes` — **copied, not FK'd**, so editing an address never rewrites history (ORD-3) |
| `delivery_zone_name` | `CharField` | snapshot |
| **Money snapshot** | Money ×8 | `subtotal`, `discount_total`, `delivery_fee`, `vat_total`, `service_charge`, `tip`, `grand_total`, `amount_paid` |
| `vat_rate_bps` | `PositiveIntegerField` | snapshot — the rate *at the time* |
| `prices_included_vat` | `BooleanField` | snapshot of the branch policy |
| `promo_code_snapshot` | `CharField(32)` blank | |
| `placed_at` | `DateTimeField` | |
| `estimated_ready_at` / `estimated_delivery_at` | `DateTimeField` null | computed ETA |
| `accepted_at` / `ready_at` / `dispatched_at` / `delivered_at` / `cancelled_at` | `DateTimeField` null | |
| `cancellation_reason` | `TextField` blank | |
| `customer_note` | `TextField` blank | |
| `idempotency_key` | `CharField(64)` unique null | |

Indexes: `(branch, status, placed_at)` for the KDS; `(user, -placed_at)` for history; `reference` unique.

### OrderItem

Full snapshot — never a live join to the catalogue.

`order` FK · `menu_item` FK null (`SET_NULL`, for analytics only) · `name_snapshot` · `description_snapshot` · `variant_name_snapshot` · `unit_price` Money · `quantity` · `line_subtotal` Money · `line_vat` Money · `tax_class_snapshot` · `special_instructions` · `image_url_snapshot`.

### OrderItemModifier

`order_item` FK, `name_snapshot`, `price_delta` (signed kobo), `quantity`.

### OrderStatusEvent  *(append-only)*

`order` FK · `from_status` · `to_status` · `actor` FK → User null · `actor_role` · `note` · `created_at` · `source` (`customer`/`staff`/`system`/`webhook`).

> **Never updated, never deleted.** This is the audit trail (ORD-8) and the `ETag` source for cheap polling (ORD-9).

---

## 9. `payments`  *(Phase 1)*

### PaymentTransaction

| Field | Type | Notes |
|---|---|---|
| `order` | FK → Order null | null for academy enrolments |
| `enrolment` | FK → academy.Enrolment null | |
| `provider` | choices | `paystack` / `flutterwave` / `bank_transfer` / `cash` |
| `provider_reference` | `CharField(120)` indexed | |
| `our_reference` | `CharField(64)` unique | what we send to the provider |
| `amount` | Money | expected |
| `amount_verified` | Money null | what the provider says was actually paid |
| `currency` | `CharField(3)` | `NGN` |
| `status` | choices | `initialised` / `pending` / `success` / `failed` / `abandoned` / `reversed` |
| `channel` | `CharField(40)` blank | `card` / `bank` / `ussd` / `qr` — reported by the provider |
| `authorization_code` | `CharField(120)` blank | **reusable token for saved cards. Never a PAN** |
| `card_last4` / `card_brand` / `card_exp_month` / `card_exp_year` | `CharField` blank | display only |
| `raw_response` | `JSONField` | full provider payload, for disputes |
| `initialised_at` / `verified_at` | `DateTimeField` | |
| `failure_reason` | `CharField(255)` blank | |

> **There is no field for a card number, and there never will be.** See `PAYMENTS.md` §1.

### WebhookEvent

`provider` · `event_id` (**unique — this is the idempotency guard**) · `event_type` · `signature_valid` `BooleanField` · `payload` JSON · `processed_at` null · `processing_error` blank · `received_at`.

### Refund

`transaction` FK · `order` FK · `amount` Money · `reason` · `status` (`pending`/`success`/`failed`) · `provider_reference` · `initiated_by` FK → User · `created_at`.

### SavedPaymentMethod  *(Phase 2)*

`user` FK · `provider` · `authorization_code` · `card_last4` · `card_brand` · `exp_month` · `exp_year` · `is_default` · `is_active`.

> Replaces `PaymentMethodsSection.tsx`'s hardcoded Visa •4242 and Mastercard •5555 — and stores only what a provider token permits.

---

## 10. `reservations`  *(Phase 2)*

### TableArea

`branch` FK, `name` (Indoor / Outdoor Patio / Private Room), `slug`, `description`, `features` JSON, `is_premium`, `surcharge` Money, `display_order`.

### RestaurantTable

**The thing the current UI has no concept of.**

`branch` FK · `area` FK · `number` `CharField(10)` · `seats_min` · `seats_max` · `is_active`.

`UniqueConstraint(branch, number)`.

### ServicePeriod

`branch` FK · `name` (Lunch / Dinner) · `weekday` · `starts_at` · `ends_at` · `slot_interval_minutes` (default 30) · `turn_time_minutes` (default 90) · `is_active`.

> Availability is **computed** from these plus live bookings. The frontend currently hardcodes 18 always-available slots.

### Reservation

| Field | Type | Notes |
|---|---|---|
| `reference` | `CharField(20) unique` | |
| `branch` | FK | |
| `user` | FK null | guests allowed |
| `table` | FK → RestaurantTable null | allocated on confirmation |
| `area` | FK → TableArea | the customer's preference |
| `reserved_for` | `DateTimeField` indexed | |
| `duration_minutes` | `PositiveSmallIntegerField` | |
| `party_size` | `PositiveSmallIntegerField` | |
| `guest_name` / `guest_email` / `guest_phone` | | |
| `special_requests` | `TextField` blank | |
| `status` | choices | `pending` / `confirmed` / `seated` / `completed` / `cancelled` / `no_show` |
| `confirmation_token` | `CharField(64)` | for the emailed cancel/modify link |
| `source` | choices | `web` / `phone` / `walk_in` |

**Double-booking prevention (RES-6)** — an exclusion constraint, not an application check:

```python
ExclusionConstraint(
    name="no_double_booked_table",
    expressions=[
        (TsTzRange("reserved_for", func.reserved_for + duration, RangeBoundary()), RangeOperators.OVERLAPS),
        ("table", RangeOperators.EQUAL),
    ],
    condition=Q(status__in=["pending", "confirmed", "seated"]),
)
```

Requires the `btree_gist` Postgres extension.

### BlackoutDate

`branch`, `date`, `reason`, `full_day`, `starts_at` null, `ends_at` null.

---

## 11. `catering`  *(Phase 2)*

### CateringPackage

`branch` FK · `name` (Essential / Premium / Luxury) · `slug` · `description` · `min_guests` · `max_guests` · `price_per_person` Money · `features` JSON list · `is_popular` · `display_order` · `is_active` · `image`.

### CateringEnquiry

Captures every field the current form collects — all of which currently go to `console.log`.

`reference` · `branch` FK · `user` FK null · `name` · `email` · `phone` · `event_type` · `event_date` · `event_time` null · `guest_count` · `package` FK null · `venue` · `message` · `indicative_total` Money (computed `guests × price_per_person`, **flagged indicative**) · `status` (`new`/`contacted`/`quoted`/`won`/`lost`) · `assigned_to` FK → User null · `internal_notes` · `quoted_amount` Money null · `responded_at` null.

Index `(status, created_at)` so managers can see enquiries breaching the promised 24-hour response.

---

## 12. `support`  *(Phase 2–3)*

### ContactMessage
`name` · `email` · `phone` · `reason` (`general`/`reservation`/`catering`/`feedback`/`partnership` — matches the existing form) · `subject` · `message` · `ip_address` · `user_agent` · `is_spam`.

### Ticket
`reference` · `contact_message` FK null · `user` FK null · `subject` · `status` (`open`/`pending`/`resolved`/`closed`) · `priority` · `assigned_to` FK null · `resolved_at`.

### TicketReply
`ticket` FK · `author` FK null · `body` · `is_internal_note` · `sent_email`.

### FaqEntry  *(Phase 3)*
`question` · `answer` · `category` · `keywords` `JSONField` · `display_order` · `is_active` · `helpful_count`. Serves both `/help` and the chat bot.

### ChatSession / ChatMessage  *(Phase 3 — ✅ delivered in 3.5)*
Session: `branch` FK · `session_token` (unique, 256-bit, compared in constant time) · `user` FK null (cascade — erased with the account) · `awaiting` (`order_reference` / `order_email` / blank) · `context` JSON · `created_at` (= started) · `updated_at` (idle expiry after 12 h) · `ended_at` · `escalated_to_ticket` FK null.
Message: `session` FK · `sender` (`user`/`bot`) · `body` · `matched_faq` FK null · `extra` JSON (`suggestions`, `can_escalate`, `action`, so a reopened transcript renders as it did) · `created_at`. Integer key, never exposed.

> The bot answers only from `FaqEntry` and an order-status lookup. It never generates prices, delivery promises or menu claims.

---

## 13. `reviews`  *(Phase 3 — ✅ delivered in 3.1)*

### Review

`user` FK · `menu_item` FK null · `order` FK null · `order_item` FK null · `rating` (1–5, `CheckConstraint`) · `title` · `comment` · `recommends` `BooleanField` · `is_verified_purchase` · `status` (`pending`/`approved`/`rejected`) · `moderated_by` FK null · `moderated_at` · `rejection_reason` · `helpful_count`.

`UniqueConstraint(user, order_item)` — one review per purchased line. `CheckConstraint` keeps `rating` within 1–5.

`MenuItem.average_rating` (one decimal place, rounded half up) and `review_count` are recomputed **synchronously** from the approved reviews whenever a review is approved, rejected, edited or deleted — one aggregate query, cheap enough not to need a task, and recomputed from scratch so the figure cannot drift. This retires the hardcoded `5.0`.

`OrderItem.public_id` (UUID, unique) is what reviews and clients reference; the integer key stays server-side.

### ReviewHelpfulVote  *(✅ delivered)*

`review` FK · `user` FK null · `voter_key` · `created_at`. `UniqueConstraint(review, voter_key)`.

`voter_key` is `user:<id>` for signed-in voters and a salted SHA-256 of the client address for anonymous ones; the address itself is never stored.

---

## 14. `academy`  *(Phase 3)*

### Instructor
`user` FK null · `name` · `bio` · `photo` · `specialities` JSON · `is_active`.
> Currently a free-text string on each course.

### Course
`title` · `slug` · `description` · `instructor` FK · `level` (`beginner`/`intermediate`/`advanced`/`masterclass`) · `type` (`cooking`/`baking`/`plating`/`business`/`nutrition`) · `duration_label` · `session_count` · `price` Money · `features` JSON · `thumbnail` · `average_rating` · `student_count` (**computed**) · `is_active`.

### Cohort
`course` FK · `starts_on` · `ends_on` · `capacity` · `enrolled_count` · `schedule_note` · `status` (`open`/`full`/`running`/`completed`/`cancelled`).
> Makes "start date" a bounded choice instead of a free-text field.

### Enrolment
`reference` · `course` FK · `cohort` FK · `user` FK null · `name`/`email`/`phone` · `experience_level` · `status` (`pending_payment`/`confirmed`/`cancelled`/`completed`) · `amount_paid` Money · `payment_method` · `certificate_issued_at` null.

Capacity is decremented inside `select_for_update()` on the cohort.

> **The "installment" payment option currently in the UI is not represented here.** Per ACA-6 it must either gain a `PaymentPlan` + `Installment` model pair or be removed from the frontend. It must not ship as unbacked copy.

---

## 15. `loyalty`  *(Phase 3)*

### LoyaltyTier
`name` (Silver / Gold / Platinum) · `min_points` · `benefits` JSON · `points_multiplier_bps` · `colour` · `display_order`.

### LoyaltyAccount
`user` O2O · `points_balance` (**denormalised from the ledger**) · `lifetime_points` · `tier` FK · `joined_at`.

### PointsLedgerEntry  *(append-only — the source of truth)*
`account` FK · `entry_type` (`earn`/`redeem`/`expire`/`adjustment`/`reversal`) · `points` `IntegerField` (**signed**) · `order` FK null · `reward` FK null · `description` · `expires_at` null · `created_by` FK null.

> A balance column alone is not acceptable (LOY-1). The ledger is what makes refund reversal (LOY-5) possible.

### Reward
`name` · `description` · `points_cost` · `reward_type` (`discount`/`free_item`/`free_delivery`) · `value` · `menu_item` FK null · `is_active` · `stock` null.

### RewardRedemption
`account` FK · `reward` FK · `order` FK null · `points_spent` · `status` · `redeemed_at`.

---

## 16. `gallery`  *(Phase 3 — ✅ delivered in 3.4)*

### GalleryImage
`branch` FK · `category` (`food`/`interior`/`events`/`team`/`ambiance`) · `title` · `description` · `image` (Supabase; jpg/jpeg/png/webp, ≤ 10 MB) · `alt_text` · `tags` M2M · `display_order` · `is_featured` · `is_active`. UUID key, timestamps.

### GalleryTag
`name` (unique) · `slug` (unique).

No photos are seeded: the 20 frontend entries pointed at files that never existed, so the gallery starts empty and the restaurant uploads real photos in the admin (like menu photos, this is owner content).

> The frontend currently defines 20 gallery items whose `imageKey`s have **no corresponding entry** in `lib/assets/images.ts`, so every one renders a placeholder icon.

---

## 17. `notifications`  *(Phase 1)*

### EmailTemplate
`key` unique (`order_confirmation`, `password_reset`, …) · `subject` · `html_body` · `text_body` · `is_active`.

### Notification  *(outbox)*
`channel` (`email` — SMS/WhatsApp reserved) · `template_key` · `recipient` · `subject` · `body` · `context` JSON · `status` (`queued`/`sent`/`failed`/`bounced`) · `provider_message_id` · `sent_at` · `error` · `related_order` FK null · `related_reservation` FK null · `attempts`.

> Every send is recorded (NOT-3). When a customer says "I never got my confirmation", this table answers the question.

---

## 18. Entity relationships (core path)

```
Branch ──< Category ──< MenuItem ──< Variant
  │                        │  └─< ModifierGroup ──< Modifier
  │                        │  └─< MenuItemImage
  │                        │  └─< AvailabilityWindow
  │                        └──>< DietaryTag
  │
  ├──< OpeningHours, HolidayOverride, DeliveryZone
  │
  └──< Order ──< OrderItem ──< OrderItemModifier
         │  └─< OrderStatusEvent        (append-only audit)
         │  └─< PaymentTransaction ──< Refund
         │  └─── DeliveryAssignment ──> RiderProfile
         │  └─< PromoRedemption ──> PromoCode
         │  └─< PointsLedgerEntry ──> LoyaltyAccount
         │
User ──┴─< Address ──> DeliveryZone
  ├──── Profile
  ├──< Cart ──< CartItem ──< CartItemModifier
  ├──< Reservation ──> RestaurantTable ──> TableArea
  ├──< Review ──> MenuItem
  ├──< Enrolment ──> Cohort ──> Course ──> Instructor
  └──── LoyaltyAccount ──> LoyaltyTier
```

---

## 19. Seed data plan

`python manage.py seed_initial` creates:

1. One `Branch` — Kuyash Place, Victoria Island, `prices_include_vat=True`, `vat_rate_bps=750`
2. `OpeningHours` for all seven days
3. Six `Category` rows matching the existing UI (What's Hot 🔥, Burgers 🍔, Chickens & Salads 🍗, Tacos/Fries & Sides 🌮, Breakfast 🥞, Desserts & Drinks 🍰)
4. The 18 `MenuItem` rows from `lib/data/menu.ts` — **each with `needs_repricing=True`**
5. Eight `DietaryTag` rows
6. Three `DeliveryZone` rows (Victoria Island, Ikoyi, Lekki Phase 1) with **placeholder** fees
7. Three `CateringPackage` rows (₦3,500 / ₦6,500 / ₦12,000 per head — already plausible naira)
8. Six `Course` rows (₦40,000–₦75,000 — already plausible naira)
9. Three `LoyaltyTier` rows
10. `LegalPage` rows seeded from the existing route files, **with the tax copy corrected**

### 19.1 The repricing gate

Every seeded `MenuItem` price is a **known-wrong dollar figure** carried over from `lib/data/menu.ts` (₦14.90 for a Signature Grill Plate, ₦10.90 for a burger). They exist only so the system has shape.

Enforcement:

- `needs_repricing` defaults to `True`
- The Django admin changelist shows a red banner: *"N items have unconfirmed prices and cannot be ordered."*
- `MenuItem` with `needs_repricing=True` is **excluded from the public catalogue API** entirely
- `manage.py check --deploy` gains a custom check that **fails** while any active item has `needs_repricing=True`

You cannot accidentally launch selling ₦14.90 burgers.
