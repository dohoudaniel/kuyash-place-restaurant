# Load tests

Targets from `docs/TESTING.md` §10:

| Scenario | Target |
|---|---|
| 200 concurrent order-status polls | p95 < 100 ms |
| 50 concurrent order placements | zero duplicates, zero lost orders |
| Menu browse, 500 rps | p95 < 200 ms (cached) |
| KDS poll, 10 clients @ 10s | no lock contention |

## Running

These require a **Postgres** environment. Running them against the SQLite
development database measures SQLite's write lock, not the application, and
will produce numbers that are both pessimistic and meaningless.

```bash
pip install locust
DATABASE_URL=postgres://... python manage.py migrate
python manage.py seed_initial
locust -f loadtests/locustfile.py --host https://staging-api.kuyashplace.com
```

## What is already covered by the test suite

Correctness under concurrency does **not** need Locust and is asserted in
`apps/orders/tests/test_concurrency.py`:

- a double-submitted order with one `Idempotency-Key` creates exactly one order;
- concurrent kitchen accepts produce exactly one transition;
- concurrent webhook deliveries settle a payment exactly once.

Locust measures *throughput and latency*. The suite measures *correctness*.
Do not use one in place of the other.
