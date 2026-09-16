# Load tests

Locust measures **throughput and latency**. Correctness under concurrency is asserted by the test suite (`apps/orders/tests/test_concurrency.py` and friends). Do not use one in place of the other.

> **These tests were rewritten on 2026-09-16.** The previous profile reported healthy numbers while three of its four scenarios measured nothing: the order poller had no order reference and returned immediately (weight 5 — roughly a third of simulated users idle), the kitchen screen called a staff-only endpoint with no credentials and measured a 403, and checkout paid by cash so the payment provider was never touched. There was no WebSocket load at all. **Every scenario now fails loudly when it cannot run**, so an idle scenario can never again look like a pass.

## Targets

From `docs/TESTING.md` §10, with what each one actually exercises now:

| Scenario | Target | Exercised by |
|---|---|---|
| Order-status polling, 200 concurrent | p95 < 100 ms | `OrderPoller` — real references from real checkouts, with `If-None-Match` |
| Order placement, 50 concurrent | zero duplicates, zero lost orders | `CashCheckout` + `CardCheckout` |
| Menu browse, 500 rps | p95 < 200 ms | `MenuBrowser` (list, filter, search, detail) |
| KDS poll, 10 clients @ 10s | no lock contention | `KitchenDisplay`, authenticated |
| Live order sockets | connection + first message under load | `OrderSocketWatcher` |

**The menu target assumes caching.** Until read-through caching exists, treat any p95 under load as a measurement of the uncached path and expect it to miss.

## Requirements

These need a **Postgres** environment. Running them against the SQLite development database measures SQLite's write lock, not the application, and produces numbers that are both pessimistic and meaningless.

```bash
pip install locust websocket-client      # websocket-client powers the socket scenario
DATABASE_URL=postgres://... python manage.py migrate
python manage.py seed_initial
```

The seeded menu items are flagged `needs_repricing` and are therefore **excluded from the public API**, so price them first or the checkout scenarios will find nothing to add to a cart.

### Environment variables

| Variable | Needed by | Notes |
|---|---|---|
| `KDS_EMAIL`, `KDS_PASSWORD` | `KitchenDisplay` | An account in the `kitchen` group on the target environment. Without it the scenario reports a failure instead of silently measuring a 403 |

## Running

```bash
locust -f loadtests/locustfile.py --host https://staging-api.kuyashplace.com
```

Headless, for CI or a scripted run:

```bash
locust -f loadtests/locustfile.py --host https://staging-api.kuyashplace.com \
       --headless --users 500 --spawn-rate 20 --run-time 10m --csv results/run
```

## Reading the results

- **`SCENARIO` rows are setup failures**, not slow requests: missing kitchen credentials, no orders available to poll, or `websocket-client` not installed. Any of them means the scenario below it measured nothing.
- **`payment initialise`** is the expensive path — an outbound HTTPS call inside the request. Watch its p95 and its share of `order place (card)`.
- **`ws order first message`** is connection to first payload, the number that matters for live tracking.
- A `304` on `order poll` should be dramatically cheaper than a `200`. If it is not, the ETag is doing no work.

## What this still does not cover

- Sustained soak (memory growth, connection leaks) — this is a burst profile.
- The webhook path, which in production is called by the provider, not by customers.
- Admin and reporting under load.
- Anything behind the real payment provider: `CardCheckout` stops at the authorization URL and never visits the hosted page, so provider-side latency is out of scope by design.
