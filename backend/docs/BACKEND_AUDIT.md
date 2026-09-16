# Backend audit — 2026-09-16

A teardown of the backend against one question: **can this run a restaurant for 5,000 concurrent users without losing money, data or customers?**

Short answer: **the correctness engineering is genuinely strong; the scalability engineering barely exists; and there are seven bugs that lose money or data today, at any scale.**

This is deliberately unflattering. What is good is listed too (§10), because an audit that praises nothing is as useless as one that praises everything.

---

## 1. Verdict

| Dimension | State | Gap to 5,000 concurrent users |
|---|---|---|
| Money correctness (pricing, VAT, ledgers) | **Strong** | None — this is the best part of the codebase |
| Payment settlement discipline | **Strong** | None in principle; the recovery paths are broken (§3) |
| Business-logic completeness | **Holed** | 7 live bugs, 2 of them lose money, 1 loses customer data |
| Idempotency | **Broken under concurrency** | Non-atomic claim, no database backstop |
| Database schema and indexes | **Good** | 5 missing indexes, no search index, 2 real N+1s |
| Caching | **Absent** | Nothing is cached. This is the single biggest scale gap |
| Process model | **Wrong shape** | Sync views on Daphne; needs a threaded HTTP server |
| Background work | **Fragile** | No retries, no dead-letter, one queue, unbounded sweeps |
| Security | **Strong, with holes** | No injection anywhere; 3 real holes, 1 privilege escalation |
| Auth flows | **Correct but unforgiving** | Silent email loss; ordinary second-click is a dead end |
| Structure | **Drifting** | Same rule implemented 7×; the canonical version is dead code |
| Observability | **Instrumented, uncollected** | Logs go nowhere; Sentry has no DSN |
| Load testing | **Fiction** | 3 of 4 scenarios measure nothing |

**Launch risk if deployed as-is:** duplicate charges that cannot be refunded, customers who pay and never get food, customers who can never sign in, and — the moment it sits behind a load balancer — the entire site rate-limited to 10 orders per hour.

---

## 2. Method, and what "verified" means here

Seven parallel audits covering business logic, payments and idempotency, database, performance and concurrency, security, auth flows, and structure. Every critical and high finding below was then **re-verified against the code by hand**, and the most surprising ones were **reproduced with throwaway tests** that were deleted afterwards.

Three claims from the audits were **rejected on verification** and are not in this report:

1. *"A deactivated account can regain a session through email verification."* **False.** `verify_email` does log the user in without an `is_active` check, but Django's auth backend refuses to load an inactive user, so the session is inert. Probe: verification returned 200, `/auth/session/` returned `user: null`. Worth tidying, not a ban bypass.
2. *"`MenuItem.order_count` is never incremented, so `sort=popular` is broken."* **False.** It is incremented at `apps/orders/receivers.py:77` with an `F()` expression on delivery.
3. *"Any browsing guest's cart is wiped when another guest pays."* **Overstated** — an idle guest is safe. The real scope is narrower and worse (§3.1).

**Not measured:** throughput. Every requests-per-second and latency figure in the performance audit is an estimate from reading code, not a profile. The process-model analysis (§6.1) is sound reasoning about asgiref's behaviour but **has not been load tested**. Treat those as hypotheses to confirm, not facts. The load tests that would confirm them are themselves broken (§8.4).

---

## 3. Bugs that lose money or data today

These are live at any scale, not scale problems.

### 3.1 P0 — Paying for one order deletes other customers' baskets · `apps/orders/receivers.py:29-36`

```python
carts = Cart.objects.filter(status=CartStatus.CONVERTED)
if order.user_id: carts = carts.filter(user_id=order.user_id)
else:             carts = carts.filter(user__isnull=True)   # every guest at this branch
for cart in carts.filter(branch=order.branch):
    cart.items.all().delete()
```

The receiver finds carts by *customer identity and branch* — never by the order's own cart. **Reproduced with a test:**

| Scenario | Basket before | After someone else pays |
|---|---|---|
| Guest A placed an order and is on the payment page; guest B pays | 1 line | **0 lines** |
| One signed-in customer with two outstanding orders; the second is paid | 1 line | **0 lines** |

`place_order` deliberately keeps a converted cart's items so a failed payment is recoverable (`placement.py:238-241`). This receiver deletes exactly those items. The second row is not a guest-collision bug: **a customer who pays for one order loses the basket attached to their other unpaid one.**

At scale this is also an outage fuse: converted guest carts are never purged (no retention task exists), so the guest branch of that query grows without bound, and every guest payment settlement iterates all of them inside the settlement transaction — during a webhook the provider will retry when it times out.

**Fix:** snapshot the cart id on the order; delete that one cart. Add a cart-purge beat task.

### 3.2 P0 — Duplicate charges cannot be refunded · `payments.py:68, 181-184` · `orders/receivers.py:181`

`initialise_payment` only checks `order.is_paid`, so two tabs or a retry produce two live checkout URLs for one order. When the second settles, `_settle` finds the order already paid and **silently skips** — no alert, no log. Then `amount_paid` is set to `order.grand_total` rather than the sum of settled transactions, and refunds are capped at `amount_paid` — so **the second charge cannot be refunded through the API at all.** Staff must use the provider dashboard.

### 3.3 P0 — A transient provider blip becomes permanent · `providers/paystack.py:112` · `tasks.py:31`

Paystack returns `status: false` for "invalid key" and "transaction reference not found" (which happens when a reference has not propagated yet). The adapter maps that to `failed`, and the reconciliation sweep only retries `INITIALISED` and `PENDING`. **A `FAILED` record is never retried.** Customer paid; order never becomes paid; nobody finds out. This is precisely the failure the sweep exists to prevent.

Related: `_get`/`_post` never call `raise_for_status()`, so a 502 HTML page raises `ValueError` — not a `RequestException` — and escapes the handler as an unhandled 500 on the customer's return.

### 3.4 P0 — Idempotency is check-then-set, with no database backstop · `common/idempotency.py:44-52`

```python
existing = cache.get(cache_key)     # both concurrent requests read None
...
cache.set(cache_key, _IN_FLIGHT, TTL_SECONDS)
```

Two genuinely concurrent submissions both proceed: two orders, two payments. There is **no unique constraint** on `idempotency_key` anywhere (`Order` and `Reservation` index it; academy does neither), so the cache is the only guard and the guard races.

Worse, the request-body hash is folded into the **cache key**, so the same `Idempotency-Key` with a different body silently creates a *second order at a different price* instead of being rejected. Standard semantics require a 4xx on key reuse with a changed payload.

The test that supposedly covers this calls `begin()` twice **sequentially in one thread**.

**Fix:** `cache.add()` (atomic `SETNX` on Redis); key on `(scope, key)` with the fingerprint in the value; add unique constraints; write a threaded test.

### 3.5 P0 — Verification emails are dispatched before commit, never retried, and silently lost · `notifications/services.py:116` · `tasks.py:11-21`

`register_user` is `@transaction.atomic`, and inside it `queue_email` calls `deliver_notification.delay(...)` directly. In production (Celery not eager) the task is published to Redis **before `COMMIT`**; a worker that picks it up first sees no such row, returns `"missing"`, and exits. No exception, no retry, no log.

`on_commit` is used exactly once in the codebase — for WebSocket pushes (`realtime/broadcast.py:63`). The correct pattern exists; it was never applied to email.

Compounding it: the task declares `max_retries=3` but **never calls `self.retry()`**; `deliver()` catches the exception, writes `FAILED`, and returns normally, so Celery sees success. There is no requeue action in the admin and no sweep task. One SMTP blip = a customer who is told to check their email, never receives it, and — because verification is mandatory — **can never sign in.**

Dev and test run Celery eagerly, so the task runs inline inside the transaction and sees its own uncommitted row. The only environment that behaves differently is production.

### 3.6 P0 — Cash orders can never be marked paid, refunded or receipted

`placement.py:153` puts cash orders straight into `CONFIRMED` with `payment_status=UNPAID`, and `CONFIRMED → PAID` is **not in the transition table**. `record_manual_payment()` — the only function that could fix it — has **zero non-test callers**: no admin action, no KDS endpoint. So for every cash order: `amount_paid` stays 0, the receipt PDF refuses forever, and `refund_order` raises "There is nothing to refund on this order."

### 3.7 P0 — Free-delivery promo codes have no enforceable limits · `placement.py:196`

The redemption ledger row is only written `if cart.promo_code is not None and priced.promo_discount:` — and `calculate_discount` returns **0** for free-delivery codes. So no `PromoRedemption` is ever recorded, and `times_used` / `times_used_by` are derived purely from that ledger. A free-delivery code with `usage_limit=1` is **infinite-use, by everyone, forever**, with no audit trail.

### 3.8 P1 — Refunds: racy, and a provider call inside a transaction · `payments.py:328-394`

`@transaction.atomic` wraps a live provider HTTP call (20s timeout). The over-refund guard reads `already` without a lock, so two managers double-clicking Refund both pass it and **both refund**. If the provider succeeds but the transaction later rolls back, money leaves with no `Refund` row. And with the connection pinned for the provider's latency, this is a direct route to connection exhaustion under load.

### 3.9 P1 — Money settles against orders that are no longer payable · `payments.py:181-184`

If an order was expired by the hourly sweep or cancelled, a late webhook marks the transaction `SUCCESS` and **falls through silently** — no `order_paid`, no confirmation, no refund, no log. The academy path handles its equivalent case loudly (`payment_for_cancelled_enrolment`); orders do not.

### 3.10 P1 — Other verified business-logic defects

| Bug | Location | Effect |
|---|---|---|
| `first_order_only` only checks whether *that code* was used | `promotions/services.py:65-69` | A customer with 200 orders qualifies for the new-customer discount |
| Promo reversal misses `EXPIRED` and `FAILED` | `orders/receivers.py:54` | Abandoning payment permanently burns a one-per-customer code. Loyalty includes both statuses — **the two ledgers disagree about the same event** |
| Promo `usage_limit` has no lock or constraint | `promotions/services.py:57` | Two simultaneous checkouts both redeem a `usage_limit=1` code |
| Discount allocated across **ineligible** lines | `carts/services/pricing.py:239` | Targeted promo on mixed tax classes mis-splits per-line VAT; you over- or under-remit |
| `TableArea.surcharge` is modelled, seeded at ₦25,000, shown to customers | `reservations/` | **Never charged anywhere.** Pure revenue loss on the highest-margin bookings |
| `record_manual_payment` never compares the amount received to the total | `payments.py:302-320` | A ₦5,000 transfer against a ₦33,120 order marks it fully paid — latent only because §3.6 means nothing calls it |
| Academy: payment after a lapsed hold confirms anyway | `academy/services.py:208-229` | Seat sold twice; at least it logs `critical` |

### 3.11 P1 — The VAT rate and currency in settings are dead constants · `base.py:544-545`

`DEFAULT_CURRENCY = "NGN"` and `DEFAULT_VAT_RATE_BPS = 750` sit under a heading that reads "Domain defaults" and have **zero readers**. Verified: every consumer imports identical constants from `apps/common/money.py:27-28`.

An operator who changes the VAT rate in the obvious place changes nothing — **tax silently stays at 7.5% with no error**. It is doubly misleading because pricing actually uses the per-branch `Branch.vat_rate_bps`. Either delete both constants or have `money.py` read them; leaving both is a trap with a wrong tax rate at the end of it.

---

## 4. Payments and idempotency, summarised

**What is right, and rarely is:** a client can never mark an order paid; webhook signatures are verified over raw bytes before parsing; the payload's amount is never trusted; amount *and* currency mismatch refuses to settle and logs `critical`; `WebhookEvent (provider, event_id)` is a real database-level idempotency guard; no float exists anywhere in the money path; provider HTTP calls are deliberately kept **outside** database transactions, with the reasoning documented — except in `refund_order`.

**What is wrong:** everything in the *recovery* layer — §3.2, §3.3, §3.4, §3.8, §3.9. Plus:

- **Zero `select_for_update` in `apps/payments/`.** Racing settlements leave the order `PAID` with the transaction row stuck `PENDING` (the second caller's `IllegalTransition` rolls back its own `SUCCESS` write).
- **The webhook makes a 20-second outbound call inside the provider's request.** Providers retry on timeout; each retry does it again.
- **A failed webhook is acked, not retried:** `processing_error` is set without `processed_at`, and the response is 200, so the provider never re-sends. Only the sweep can recover it — and per §3.3 the sweep skips `FAILED`.
- **The webhook endpoint is unauthenticated and unthrottled**, and persists the full attacker-controlled payload on *invalid* signatures with a unique per-request `event_id`, so dedupe never fires (§7.2).
- **Flutterwave refunds target the wrong identifier** — we store the `tx_ref` in `provider_reference`, never the provider's numeric transaction id (the numeric id goes into `authorization_code`). *Suspected*: needs a sandbox call to confirm the refund endpoint rejects it.
- **Currency is hardcoded `NGN` on initialise but compared on verify** — a non-NGN branch would charge in naira and then fail every verification.

---

## 5. Database

**The schema is better than the average production system.** Composite indexes exist for nearly every access pattern asked about: orders by user and date, orders by branch/status/date, reviews by item and status, payments by reference and status, webhooks by provider and event id, reservations by table and time, carts by token and user. FKs are all indexed; soft delete does not cause full scans (there is no global filtering manager, which is the usual trap); cursor pagination is used for append-only feeds with the reasoning documented.

**Measured query counts** (subagent, with scaling curves at 5/10/20/40 rows):

| Endpoint | Queries | Scaling |
|---|---|---|
| Order detail (30 lines) | 7 | **flat** |
| Order history (25 orders) | 7 | **flat** |
| Cart (20 lines) | 14 | **flat** |
| Menu list (30 items) | 8 | **flat** |
| **KDS queue (20 tickets)** | **50** | **+1 per ticket — N+1** |
| **Academy courses (8 courses)** | **29** | **+3 per course — N+1** |

### Findings

1. **`get_current_branch()` is uncached and called 38 times across the app** — 2–3 redundant `SELECT`s on every request, on a single-row table that changes never. The damning detail: `CURRENT_BRANCH_CACHE_KEY = "core:current_branch_id"` is **declared in the same module and never used.** The cache was designed and not implemented. Cheapest high-value fix in this document.
2. **KDS rider N+1** — `_kds_rider()` queries `DeliveryAssignment` per ticket; the queue prefetches only `items__modifiers`. This is the kitchen's primary screen, polled every 10s per screen, worst exactly when the restaurant is busiest.
3. **Academy `seats_left` N+1** — one `COUNT(*)` per cohort, on an **unpaginated** course list.
4. **`Order.placed_at` is completely unindexed**, and every report plus the KDS summary range-filters on it.
5. **No full-text index exists.** Menu search builds `SearchVector` at query time and ranks — a full scan per search, plus an `icontains` fallback that can never use an index. `base.py` explicitly promises GIN indexes "in Phase 1/2"; the exclusion constraint shipped, the GIN index did not.
6. **Missing composites:** loyalty ledger `(account, -created_at)`, review moderation `(status, created_at)`, `Cart.expires_at`, and a KDS-shaped `(branch, status, placed_at)` (the queue filters on one index and sorts on another).
7. **JSON blobs are never deferred** — `raw_response`, `payload`, `Notification.body`/`html_body` are fetched in full on every row read.
8. **Reports pull whole result sets into Python** — up to 366 days of orders, in a synchronous request, bucketed row by row.
9. **`loyalty.expire_inactive` is one query per account** — 50k members, 50k queries, in a task with a 240s soft limit.
10. **Migrations all take `ACCESS EXCLUSIVE` locks.** Harmless on today's empty tables; the pattern will lock production tables on the next change. `orders/0002` is the worst: a Python row-by-row backfill followed by a non-concurrent unique index on the table behind order history and the KDS.
11. **`DeliveryZone.areas` is a JSON list, substring-matched in Python** on every address save and every checkout price.
12. **`LoyaltyAccount.points_balance` can drift** — read-modify-write under a lock that only exists on Postgres, with no reconciliation job against the ledger sum.

---

## 6. Performance and concurrency at 5,000 users

### 6.1 The process model is the multiplier on everything

The deployment doc prescribes Daphne, every view in the codebase is synchronous, and Django adapts sync views onto asgiref's **thread-sensitive executor** — so a Daphne process serves roughly **one synchronous request at a time**, and the WebSocket consumers' `database_sync_to_async` calls contend for that same thread.

If that holds under test, the consequences are structural: per-process throughput is `1 / request_latency`; any slow call stalls everything behind it (a Paystack timeout freezes that process for 20 seconds); 5,000 users at a modest 0.5 req/s need on the order of 80–100 processes for HTTP alone; and Daphne has no multi-process mode. Nothing in the deployment doc specifies replica counts, worker sizing or a connection pooler.

**This is the one finding I most want load-tested before acting on it** — the reasoning is sound, the numbers are not measured.

### 6.2 Nothing is cached. Anywhere.

Verified by exhaustive grep: the cache is used in exactly four places — MFA lockout counters, the ops heartbeat, the health probe, and idempotency. **Not one read path is cached.** No `cache.get_or_set`, no `cached_property` on a hot path, no per-request memo, and no invalidation infrastructure to build on.

`/core/branch/` alone costs **~20 queries** (opening hours, holiday overrides, a `next_opening` loop of up to 8 days at 2 queries each, and `is_open_now` computed twice) — and the frontend calls it on every page load.

Meanwhile `docs/ARCHITECTURE.md` documents a Redis caching layer with per-model TTLs and "bust on save". **It does not exist.**

### 6.3 Synchronous work that should not be

| Work | Where | Cost |
|---|---|---|
| Provider HTTP (init, verify, refund) | 6 request-path endpoints | 300–800ms typical, 20s timeout, ×2 on fallback |
| Webhook settlement | `webhooks.py:115` | The provider waits for our provider call |
| PDF receipts and certificates | `receipt.py`, `academy/services.py` | Pure CPU, regenerated every download, never cached |
| Reports | `reporting/services.py` | Whole result set into Python, polled by the KDS summary |
| Email template lookup + insert + enqueue | inside `transition()`'s transaction | Holds an order row lock through it |
| Per-line INSERTs at placement | `placement.py:171-193` | ~40 statements where 2 `bulk_create`s would do |
| Reservation availability | `availability.py:165` | One query **per slot** — ~24 per request, public and unthrottled |

### 6.4 Background work is fragile

One queue, no routing, no priorities — a dinner-rush email backlog delays payment reconciliation by exactly that backlog. No `acks_late`, so a worker death loses the task silently. `verify_pending` makes a serial blocking HTTP call per record with no chunking and no cursor: at a 20s timeout, **12 records exhaust the 240s soft limit**, and the same prefix is re-processed every 10 minutes while the tail is never reached — during exactly the provider incident it exists to recover from.

### 6.5 HTTP layer

No gzip middleware. No `Cache-Control` or `Vary` on anything, so no CDN or browser cache can help. ETag covers exactly one endpoint — the right one — but its own implementation re-queries the events it already prefetched. 14 list endpoints have no pagination; two of them (`KDSQueueView`, `KDSItemsView`) are genuinely unbounded, and the KDS queue lets the **caller choose the status filter**, so a kitchen user can ask for every order ever placed with full line detail.

### 6.6 The launch-day landmine

`TRUSTED_PROXY_COUNT` defaults to `0`. Behind any load balancer that means every visitor shares the balancer's IP, so `anon: 100/min` becomes 100 requests per minute **for the entire site**, and `order_create: 10/hour` becomes **ten orders per hour, total**. The `kuyash.W021` check anticipates exactly this — but `Makefile:54` runs the deploy check with `|| true`, so CI can never fail on it.

Second-order: even correctly configured, per-IP limits behave badly against Nigerian carrier-grade NAT, where many customers share few addresses. Checkout throttles should key on cart or session, not IP.

---

## 7. Security

**No SQL injection, no command injection, no template injection, no SSRF, no path traversal, no mass assignment.** Searched for all of them. Sorting is dict-lookup allowlists; the only raw SQL is a literal `SELECT 1` health probe; the only outbound calls are to hardcoded provider constants. Guest-token comparisons are timing-safe and consistently return 404 rather than 403. Identifier entropy is high. Client-IP handling is exemplary.

The real holes:

### 7.1 P1 — CSV formula injection, escalating from rider to manager

`csv_response` writes values straight through `csv.writer` with no neutralisation. A rider can `PATCH /accounts/me/` with `full_name = "=cmd|'/c ...'!A1"` (no character validation), a manager opens `/reports/riders/?export=csv` in Excel, and gets a DDE prompt. **Lowest staff role to highest, via a spreadsheet.**

### 7.2 P1 — Unauthenticated, unthrottled, unbounded webhook storage

`AllowAny`, `authentication_classes = []`, no throttle scope, and on an **invalid** signature it still persists the full 5 MB-capable payload with a unique per-request `event_id` so dedupe never applies. 100 requests/minute/IP of junk, written to Postgres, never purged (no retention task exists, though the docs promise 90 days).

### 7.3 P1 — A second, unreviewed auth surface is live

Verified with a probe: `GET /_allauth/browser/v1/account/email` returns **200** for a signed-in customer. The custom serializer deliberately makes `email` read-only, documenting that changing it must re-verify and notify the old address — and the headless surface lets a customer add and promote an email address without any of that. `/_allauth/app/v1/` is mounted too, issuing session tokens for a client the frontend never uses.

### 7.4 P2 — Any rider or kitchen account can read every order's PII

`_may_read` grants access on group membership alone, with no scoping to an assigned delivery: full name, phone, street, area, landmark, delivery notes, and the receipt PDF — for every order in the business.

### 7.5 P2 — Secrets in URLs, and email-as-password

Reservations accept `?token=`, and academy emails a `manage_url` containing the guest token — both contradicting the project's own rule that tokens must not travel in URLs. Catering and support authenticate by `?email=` in the query string: the email is not a secret, and both endpoints are unthrottled.

### 7.6 P2 — Public endpoint leaks internal mailboxes

`SiteSettingsSerializer` uses `exclude` rather than an allowlist, so `support_email` and `orders_email` — the addresses internal alerts are delivered to — are served unauthenticated, and any field added later is published automatically.

### 7.7 P2 — WebSockets accept before authorising

`OrderConsumer.connect()` calls `accept()` first, and on failure simply returns without closing. Unauthorised sockets stay open indefinitely with no idle timeout and no connection cap.

### 7.8 Documented, not implemented

`SECURITY.md` is the pre-launch gate, so these matter: the NDPR data-export endpoint it claims (`/accounts/me/export/`) **does not exist**; the retention table has **no purge task**; the promised query timeouts are absent; django-axes is claimed and **not installed**; the COD fraud cap is claimed and absent.

---

## 8. Auth, UX and the rest

### 8.1 The second-click dead end

Clicking a verification link twice — from a second device, a mail-client prefetch, or a refresh — shows **"Link not valid"**, because allauth's key lookup filters on `verified=False`. The page then offers a resend, the resend endpoint silently does nothing for an already-verified address, and the page still says *"a new link is on its way."* So the app tells a fully verified customer their link is broken, then promises an email it has decided not to send, and never suggests simply signing in.

### 8.2 Other verified auth findings

- **Resend-verification has no per-IP throttle** — declaring `throttle_classes` replaces the global anon throttle, and the class it declares keys only on the submitted email. One host can send 3 emails/hour to unlimited addresses: a mail-bomb amplifier on the restaurant's sending reputation.
- **Registration is an enumeration oracle** where every other endpoint is careful — and the most common real state (registered, never verified, thanks to §3.5) dead-ends on "An account with this email already exists" with no resend affordance.
- **`invalid_token` is overloaded** for dead links *and* weak passwords, so the frontend regexes the prose to tell them apart — directly violating the codebase's own "branch on the code, never on the message" contract.
- **Every failed login costs 2× Argon2** (~246ms, ~200 MiB-ms) because two backends each hash. The silver lining is genuine: wrong-password and unknown-email are within 5ms of each other, so there is no timing oracle.
- **A session row is written on every request** (`SESSION_SAVE_EVERY_REQUEST` with database-backed sessions), making `django_session` the hottest write table in the system.
- **MFA elevation never expires** within a 14-day rolling session — the second factor is a one-time gate, not an ongoing control.
- **Recovery codes are shown once with no download**, and reset is superuser-only with no CLI break-glass. A sole superuser who loses their phone locks the whole admin out mid-service.

### 8.3 Structure and dead code

- **"Who may see this object?" is implemented seven times** with four different definitions of "staff" and three different token sources. The canonical `IsOwnerOrStaff` in `common/` is referenced **only by its own test** — dead in production. Changing one authorisation rule means finding seven places.
- **The money wire format is hand-rolled in `carts/serializers.py`** and imported by five other apps, while the real `Money` value object in `common/money.py` — which returns exactly that shape — is **unused**. There are five separate money formatters, one of which does float division on kobo.
- **Idempotency is copy-pasted into three views**, including the `MissingIdempotencyKey` class, three times identically.
- **`price_cart` is 283 lines with five levels of nesting** on the most critical path, with mid-function imports dodging circular imports that the layering created.
- **Two parallel error hierarchies** (`AuthError` hand-translated back into `DomainError` via a dict) and three parallel response conventions, one of which is invisible to the schema generator the frontend types come from.
- **The documented architecture describes a system that was not built**: four signals that don't exist, a caching layer that doesn't exist, five Celery tasks that don't exist. `API_SPEC.md` documents a ticket-replies route that is not mounted.
- **The API surface itself is clean** — 87 routed endpoints, and **every path the frontend calls resolves**; no stale or broken calls. Exactly one dead serializer (`MenuItemPriceSerializer`), whose `ref_name = "Money"` would collide with the real money schema if anyone wired it up. 17 endpoints have no frontend caller: 10 are manager tools awaiting an ops console, 7 are genuine dead weight.
- **`GET /api/v1/orders/` returns 405** — the route is named `create`/list but the view implements only `post`. History lives at `/orders/mine/`.
- **Orphaned settings:** `PAYSTACK_PUBLIC_KEY` and `FLUTTERWAVE_PUBLIC_KEY` are never read (the browser gets its keys from `NEXT_PUBLIC_*`).

### 8.4 The load tests measure almost nothing

`OrderPoller` has `reference = ""` and returns immediately — **~30% of simulated users are idle**, and the headline "200 concurrent order polls" target is never exercised. `KitchenDisplay` is unauthenticated against a staff-only endpoint, so it measures a 403. `Checkout` posts `payment_method: "cash"`, so the most expensive path in the system is untested. There is no WebSocket load at all. And the README's targets assume caching that does not exist.

### 8.5 The test suite is strong, and blind in specific places

1,143 tests, every app has a `tests/` package, no sleeps, no real network (an autouse fixture fails loudly on any unmocked HTTP call), no query-count assertions, no test classes. CI gates money paths at 100% and fails the build if a Postgres-gated test was skipped. That is well above average.

What it cannot see:

- **The idempotency race is invisible by construction.** LocMemCache is single-process, and every idempotency test is sequential — including the one whose module docstring claims to "measure that concurrency cannot corrupt state".
- **Eager Celery makes an eager-only truth look like a fact.** `test_outbox.py` asserts a notification is `SENT` immediately after queueing; in production the caller sees `QUEUED`.
- **The reservation exclusion constraint — "the guarantee Gate 2 requires" — is asserted nowhere.** The one test of its behaviour monkeypatches `Reservation.objects.create` to raise. If the constraint were dropped, CI would stay green, because the application lock alone passes the concurrency test.
- **The only real data migration is untested** (`orders/0002` backfills `public_id` then makes it unique).
- **8 of 18 `admin.py` modules have zero coverage**, including the payments read-only guards that stop an admin hand-editing a settled transaction, and the reservations actions that mutate booking state. 48 models are registered; 12 have a page loaded in a test. One parametrised "every admin page renders" test would close most of it.
- **11 of 18 throttle scopes are never exercised**, and the structural test checks the throttle class is installed but not that the scope name resolves to a configured rate — so a typo silently disables a limit.
- **`deliver_notification` is never invoked as a task**, which is why its phantom `max_retries` went unnoticed.
- **No test proves a failing receiver cannot roll back a paid order** — `notify_customer` runs inside `transition()`'s transaction.
- **Known flake:** the MFA suite computes TOTP codes from the real clock; a 30-second bucket rollover between generating and posting fails the test.
- **Postgres-only branches carry `# pragma: no cover`**, so the 100% gate passes *while the row-locking code is uncovered*.

---

## 9. Where this needs to be for 5,000 concurrent users

**Correctness first — none of the below matters if the system charges twice and loses baskets.**

1. **Fix §3 in order.** Cart scoping, duplicate-charge detection with `amount_paid` derived from settlements, `FAILED → PENDING` for transient provider errors, `cache.add()` plus unique constraints, `on_commit` plus real retries for email, a cash-collected path, and the free-delivery ledger row.
2. **Process model.** Move HTTP to Gunicorn with threaded or gevent workers (it is already a dependency); leave Daphne for `/ws/` only. Decide a replica count from a real load test.
3. **Connections.** PgBouncer in transaction mode is mandatory at this concurrency, with `CONN_MAX_AGE=0` behind it and `DISABLE_SERVER_SIDE_CURSORS=True`. Cap the channels thread pool explicitly.
4. **Caching layer, built deliberately.** Read-through Redis caching with signal-based invalidation for branch, site settings, opening hours, menu, FAQ, legal pages and loyalty tiers; a per-request memo plus a cached id for `get_current_branch` (the key already exists). Add `Cache-Control` and gzip, and extend conditional GET to the menu.
5. **Move work off the request path.** Webhook settlement into a task that acks immediately; PDFs rendered once and stored; reports as SQL aggregates, cached, with the KDS summary on its own short TTL; emails via `on_commit` with retries, `acks_late`, and separate queues for email, payments and ops.
6. **Database.** Add the five missing indexes and a stored `search_vector` with a GIN index; fix the two N+1s; `defer()` the JSON blobs; `bulk_create` order lines; batch `expire_inactive`; adopt non-locking migration patterns (`AddIndexConcurrently`, `NOT VALID` then `VALIDATE`) before the tables are big.
7. **Sessions.** `cached_db` or a Redis engine, and drop `SESSION_SAVE_EVERY_REQUEST`.
8. **Rate limiting that survives reality.** `TRUSTED_PROXY_COUNT=1`, remove the `|| true` so CI can fail on it, and key checkout throttles on cart or session rather than IP.
9. **Close the security holes.** CSV neutralisation, webhook throttle and payload cap, decide on one auth surface, scope rider access, tokens out of URLs, an allowlist on site settings, and authorise WebSockets before accepting.
10. **Then prove it.** Fix the load tests, add a WebSocket scenario, run them, and set real SLOs. Ship logs somewhere durable and set the Sentry DSN — today the instrumentation exists and nothing collects it.

**Consolidation work that pays for itself:** one authorisation rule, one money envelope, one idempotency decorator, and `price_cart` split. Four changes, all onto code that already exists, all reducing the number of places a future bug can hide.

---

## 10. What is genuinely good

Not padding — these are the parts to leave alone, and they are why this is a fixable codebase rather than a rewrite:

- **`common/money.py`** — integer kobo, `Decimal` intermediates, one rounding point, largest-remainder allocation that reconciles exactly, `bool` explicitly rejected as an `int`. Exemplary.
- **Server-authoritative pricing.** No price field on any input serializer; `expected_total` refuses rather than charges; every cart read reprices from live data.
- **Payment settlement discipline.** Raw-body HMAC before parsing; the payload's amount never trusted; amount *and* currency mismatch refuses and logs `critical`; a database unique constraint as the webhook idempotency guard; and the deliberate, documented decisions about where *not* to be atomic.
- **The order state machine.** An explicit transition table, role gating, row locking on Postgres, an append-only event log, and `status` assigned nowhere else.
- **The loyalty ledger.** Append-only with an enforced guard, database-unique idempotency keys, conditional stock decrement, and reversal that correctly does not credit lifetime points. This is the pattern payments should copy.
- **`realtime`** — `on_commit`, per-transaction dedupe, payload built once not per subscriber, failures never reaching the order.
- **`recompute_item_rating` rebuilds rather than nudges** — the single best drift-prevention decision in the codebase.
- **Custom deploy checks** turning "reprice before launch" and "the terms page must not contradict the VAT policy" into build failures.
- **Reservations** — a Postgres exclusion constraint, not just application logic.
- **CI** — dual SQLite/Postgres runs, a guard that fails if a Postgres-gated test was skipped, a backup/restore drill, `makemigrations --check`, pip-audit, gitleaks.
- **1,143 tests** against 24k lines of application code, and several of them exist because someone ran the real frontend against a real server and found real bugs.

---

## 11. What was not verified

Honesty about the edges of this audit:

- **No throughput was measured.** Every rps and latency figure is an estimate from code reading.
- **The single-threaded process model is inference**, not a profile.
- **The Flutterwave refund identifier** needs a sandbox call to confirm.
- **Deadlock risk** from inconsistent lock ordering between checkout and refund is reasoned, not reproduced.
- **Deadlock risk** between checkout and refund lock ordering is reasoned, not reproduced.
- The **Flutterwave refund identifier** and the **non-NGN currency** findings need a sandbox call to confirm.
- The default test run uses SQLite, eager Celery, locmem cache, MD5 hashing, no throttling and no MFA — each individually defensible, collectively meaning **the default suite exercises no row locking, no cache eviction, no throttling and no MFA**.
