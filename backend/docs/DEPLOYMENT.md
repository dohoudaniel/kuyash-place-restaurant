# Deployment

**Status:** target not yet chosen. This documents a recommended default plus alternatives, so the choice can be made later without reworking the application.

---

## 1. Environments

| Environment | Purpose | Data |
|---|---|---|
| `local` | Plain virtualenv, no daemons (ADR-015) | Seeded fixtures |
| `staging` | Pre-production verification, provider **test** keys | Anonymised copy |
| `production` | Live | Real |

Settings modules: `config.settings.dev` · `config.settings.test` · `config.settings.prod`. `prod.py` **raises at import** on any missing required variable — a misconfigured deploy fails immediately rather than at the first customer order.

---

## 1a. Local development (no Docker)

Local development deliberately requires **no database server, no Redis and no containers**.

```bash
cd backend
make venv install        # virtualenv + dependencies
cp .env.example .env     # defaults already work as-is
make migrate seed
make run                 # http://localhost:8000/api/v1/docs/
```

What the defaults give you:

| Component | Local default | Switch to the real thing |
|---|---|---|
| Database | SQLite (`db.sqlite3`) | `DATABASE_URL=postgres://…` |
| Cache | In-memory `LocMemCache` | `REDIS_URL=redis://localhost:6379/0` |
| Celery | Eager — tasks run in-process | Set `REDIS_URL`, then `celery -A config worker -l info` |
| WebSockets | `make run` serves ASGI through Daphne; in-memory channel layer | Set `REDIS_URL` (the channel layer switches to Redis automatically) |
| Email | Printed to the console | Set `EMAIL_BACKEND` and provider credentials |
| Media | Local `media/` directory | Set `SUPABASE_S3_ENDPOINT` and keys |

**The one caveat.** SQLite is not Postgres. Two Phase 1/2 features depend on
Postgres specifically — full-text menu search (GIN) and the reservation
double-booking `ExclusionConstraint`. Develop and test those with `DATABASE_URL`
pointed at a real Postgres; `settings.USING_POSTGRES` guards the code paths, and
from Phase 1A CI runs the suite against both engines so divergence fails the
build rather than reaching a customer.

---

## 2. Recommended default

```
Frontend    Vercel (Next.js 16, already the natural home)
Backend     Managed PaaS — Railway, Render or Fly.io
Database    Managed Postgres 16 with PITR
Cache/queue Managed Redis 7 (also the WebSocket channel layer)
Web         daphne -b 0.0.0.0 -p $PORT config.asgi:application   (ASGI: HTTP + WebSockets)
Workers     Separate Celery worker + beat services
Media       Supabase Storage (decided)
Email       Resend or Postmark
Monitoring  Sentry + the platform's metrics
```

**Why:** one backend developer, no dedicated ops. Managed Postgres with point-in-time recovery is worth more than the monthly saving of self-hosting, and the DNS requirement below is trivial to satisfy.

### 2.0 Frontend rendering and CSP

The frontend sets a nonce-based Content Security Policy in `proxy.ts`, so every page renders per request (a prebuilt page cannot carry a per-request nonce). On Vercel this is automatic; elsewhere, run `next start` behind the proxy rather than exporting static files, and do not cache HTML at a CDN edge (static assets under `/_next/static` still cache normally). `NEXT_PUBLIC_API_URL` must be set at build time: the policy's `connect-src`, `img-src` and `form-action` are derived from it.

### 2.1 The DNS requirement (not optional)

Session-cookie auth requires a shared parent domain:

```
kuyashplace.com          → Vercel (frontend)
api.kuyashplace.com      → Django (backend)
```

with `SESSION_COOKIE_DOMAIN = ".kuyashplace.com"`. If the backend ends up on a platform subdomain (`kuyash.up.railway.app`), cookies will not be shared and auth silently breaks. **Set up the custom domain before writing auth code.**

---

## 3. Alternatives

### 3.1 VPS (DigitalOcean / Hetzner / Contabo)

Cheapest at scale; you own the ops.

```
Nginx (with WebSocket upgrade headers) → Daphne (Django ASGI) + Celery worker + beat
Postgres + Redis on the same box (or managed, recommended)
Certbot for TLS · UFW · fail2ban · unattended-upgrades
```

Deploy via Docker Compose + a pull-and-restart script, or systemd units. **You must set up and test your own backups** — this is where self-hosted deployments usually fail.

Rough cost: $12–24/month for the box.

### 3.2 AWS

Most control, most complexity. ECS Fargate or EC2 + RDS Postgres + ElastiCache Redis + ALB + Secrets Manager. Media still Supabase (already decided), so no S3/CloudFront work needed. Warranted only if you have AWS expertise or a compliance requirement.

### 3.3 Comparison

| | PaaS | VPS | AWS |
|---|---|---|---|
| Setup time | Hours | 1–2 days | 3–5 days |
| Monthly (low traffic) | $25–60 | $12–24 | $60–120 |
| Ops burden | Low | High | Medium-high |
| Backups | Included | **Your job** | Included (RDS) |
| Scaling | Slider | Manual | Auto |
| **Recommended for this project** | ✅ | if cost-driven | only with expertise |

---

## 4. Environment variables

```bash
# ── Core ────────────────────────────────────────────────────────────────
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<50+ random chars>
# Admin two-factor step (default true). Rotating DJANGO_SECRET_KEY makes staff re-enrol their authenticator app.
STAFF_MFA_REQUIRED=true
# Proxies in front of Django that append to X-Forwarded-For (Nginx or the platform load balancer: 1).
# 0 behind a proxy puts every visitor on one IP, so one person's failed logins throttle everyone (kuyash.W021).
TRUSTED_PROXY_COUNT=1
# Optional: addresses/CIDR ranges allowed to reach the admin; everyone else gets 404. Empty = off.
ADMIN_ALLOWED_IPS=
DEBUG=False
ALLOWED_HOSTS=api.kuyashplace.com
FRONTEND_URL=https://kuyashplace.com

# ── Data ────────────────────────────────────────────────────────────────
DATABASE_URL=postgres://user:pass@host:5432/kuyash
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/1
CELERY_RESULT_BACKEND=redis://host:6379/2

# ── Cookies / CORS ──────────────────────────────────────────────────────
SESSION_COOKIE_DOMAIN=.kuyashplace.com
CSRF_TRUSTED_ORIGINS=https://kuyashplace.com,https://www.kuyashplace.com
CORS_ALLOWED_ORIGINS=https://kuyashplace.com,https://www.kuyashplace.com

# ── Payments ────────────────────────────────────────────────────────────
PAYSTACK_SECRET_KEY=sk_live_xxx
PAYSTACK_PUBLIC_KEY=pk_live_xxx
FLUTTERWAVE_SECRET_KEY=FLWSECK-xxx
FLUTTERWAVE_PUBLIC_KEY=FLWPUBK-xxx
FLUTTERWAVE_WEBHOOK_SECRET_HASH=xxx
DEFAULT_PAYMENT_PROVIDER=paystack
PAYMENT_CALLBACK_URL=https://kuyashplace.com/checkout/complete

# ── Media (Supabase Storage) ────────────────────────────────────────────
SUPABASE_S3_ENDPOINT=https://<project-ref>.supabase.co/storage/v1/s3
SUPABASE_BUCKET=kuyash-media
SUPABASE_REGION=eu-west-1
SUPABASE_S3_ACCESS_KEY=xxx
SUPABASE_S3_SECRET_KEY=xxx
# Optional — derived from the endpoint and bucket when blank:
# https://<project-ref>.supabase.co/storage/v1/object/public/<bucket>
SUPABASE_PUBLIC_URL=

# ── Email ───────────────────────────────────────────────────────────────
EMAIL_BACKEND=anymail.backends.resend.EmailBackend
RESEND_API_KEY=xxx
DEFAULT_FROM_EMAIL="Kuyash Place <orders@kuyashplace.com>"

# ── Observability ───────────────────────────────────────────────────────
SENTRY_DSN=https://xxx
SENTRY_ENVIRONMENT=production
LOG_LEVEL=INFO
```

Frontend (`NEXT_PUBLIC_*` is visible to anyone — **public keys only**):

```bash
NEXT_PUBLIC_API_URL=https://api.kuyashplace.com/api/v1
NEXT_PUBLIC_PAYSTACK_PUBLIC_KEY=pk_live_xxx
```

---

## 5. Supabase Storage setup

1. Create a bucket `kuyash-media`, **public read** (menu and gallery images are public)
2. Generate S3 access keys under Project Settings → Storage → S3 Access Keys
3. Configure `django-storages`:

```python
STORAGES = {"default": {"BACKEND": "storages.backends.s3.S3Storage"}}
AWS_S3_ENDPOINT_URL     = env("SUPABASE_S3_ENDPOINT")
AWS_STORAGE_BUCKET_NAME = env("SUPABASE_BUCKET")
AWS_S3_CUSTOM_DOMAIN    = supabase_public_domain(...)   # see below
AWS_S3_REGION_NAME      = env("SUPABASE_REGION")
AWS_ACCESS_KEY_ID       = env("SUPABASE_S3_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY   = env("SUPABASE_S3_SECRET_KEY")
AWS_S3_ADDRESSING_STYLE = "path"        # Supabase requires path style
AWS_QUERYSTRING_AUTH    = False         # public URLs, no signing
AWS_S3_FILE_OVERWRITE   = False
```

4. **Add the Supabase hostname to `frontend/next.config.ts` → `images.remotePatterns`.** That file is currently empty, so remote images will silently fail to render.

---


### 5.1 Reads and writes use different URLs

Supabase Storage has two faces. **Writes** go through the S3-compatible endpoint,
which needs signed requests. **Public reads** go through
`/storage/v1/object/public/<bucket>/`.

Left to itself, django-storages builds image URLs against the write endpoint —
`https://<ref>.supabase.co/storage/v1/s3/<bucket>/<key>` — and every menu and
gallery photo fails to load. `AWS_S3_CUSTOM_DOMAIN` is therefore set from
`apps.common.storage.supabase_public_domain`, which derives the public path from
`SUPABASE_S3_ENDPOINT` and `SUPABASE_BUCKET`. Set `SUPABASE_PUBLIC_URL` only if
images are served through a CDN in front of Supabase.

The bucket itself must be marked **public** in the Supabase dashboard. The
frontend's `next.config.ts` allows `**.supabase.co/storage/v1/object/public/**`
and nothing else from Supabase.

## 6. Provider webhook configuration

| Provider | Dashboard setting | URL |
|---|---|---|
| Paystack | Settings → API Keys & Webhooks | `https://api.kuyashplace.com/api/v1/webhooks/paystack/` |
| Flutterwave | Settings → Webhooks (+ secret hash) | `https://api.kuyashplace.com/api/v1/webhooks/flutterwave/` |

Verify after deploy by sending a test event and checking that a `WebhookEvent` row appears with `signature_valid=True`.

---

## 7. Release process

```
1. CI green on main (lint, types, tests, coverage gates, security gates)
2. Deploy to staging
3. Run migrations:  python manage.py migrate
4. Smoke test on staging with provider TEST keys:
     register → verify → add to cart → apply promo → checkout → pay → KDS advance → delivered
5. Tag the release
6. Deploy to production
7. Run migrations
8. Verify: /health/, OpenAPI docs, a real ₦100 test order, refund it
9. Watch Sentry and logs for 30 minutes
```

**Migrations run as a separate, explicit step** — never automatically on container start, where a failure would take the whole service down.

### 7.1 Zero-downtime migrations (Phase 2+)

Expand-and-contract: add nullable columns first; backfill in a data migration; switch code; drop old columns in a later release. Never rename or drop a column in the same deploy that stops using it.

---

## 8. Backups

| What | How | Retention |
|---|---|---|
| Postgres | Automated daily + PITR | 30 days |
| Media | Supabase built-in | Per plan |
| Secrets | Encrypted offline copy | Rotated annually |

**A backup you have never restored is not a backup.** Restore to a scratch database quarterly and record the date. This is a Gate 1 checklist item.

### 8.1 Portable dump

The platform's daily backups and PITR are the primary copy. Take a portable one before a risky migration, to keep off-platform, or for a drill:

```bash
DATABASE_URL=postgres://… ./scripts/backup-db.sh            # → backups/kuyash-<UTC>.dump + .sha256
```

It uses `pg_dump` custom format without owners or grants (restorable into any role's database), and reads the archive back to confirm it is complete and contains `django_migrations`. Dumps hold customer data: `backups/` and `*.dump` are git-ignored; store them encrypted and delete them after the retention period.

### 8.2 Restore drill

```bash
# An EMPTY scratch database, never the live one; same SECRET_KEY as the source.
./scripts/restore-drill.sh backups/kuyash-<UTC>.dump postgres://…/kuyash_restore --max-age-hours 26
```

The drill checks the checksum, refuses to restore over `DATABASE_URL` (compared without credentials, scheme spelling or query string) or into a database that already has tables, restores with `--exit-on-error`, then runs `manage.py verify_restore`:

| Check | Fails when |
|---|---|
| `migrations` | the code has migrations the dump lacks (an old dump, a partial restore) |
| `order_totals` | an order's `grand_total` no longer equals subtotal − discount + delivery + service charge (+ VAT when exclusive) + tip |
| `order_lines` | an order's lines don't sum to its subtotal (missing or duplicated items) |
| `paid_orders` | a card or transfer order marked paid has no successful payment record |
| `loyalty_balances` | a points balance differs from the sum of its ledger |
| `staff_mfa_secrets` | *warning only* — authenticator secrets don't decrypt with this `SECRET_KEY`; those staff would have to re-enrol |
| `freshness` (`--max-age-hours`) | the newest order or sign-up is older than the limit (a stale dump) |

`verify_restore` is read-only and can also be run against production as a consistency check. CI runs the whole drill on a seeded database on every change (the Postgres job), so the scripts are known to work; the drill on real staging data is the launch task.

| Date | Dump | Duration | By |
|---|---|---|---|
| — | *no drill on real data yet* | | |

---

## 9. Monitoring and alerts

| Signal | Threshold | Route |
|---|---|---|
| 5xx rate | > 1% over 5 min | Page |
| Payment webhook failures | any invalid signature | Page |
| `verify_pending_payments` finds stale txns | > 5 in one run | Page |
| Order placement p95 | > 2 s | Warn |
| Celery queue depth | > 100 | Warn |
| Orders stuck in `preparing` | > 60 min | Daily report |
| Disk / connection pool | > 80% | Warn |
| Certificate expiry | < 14 days | Warn |

`/health/` returns database and cache status (503 if either fails) and, with a broker, `scheduler`: `ok`, `not seen` or `stale: last run Ns ago` from the beat heartbeat. A stale scheduler does not fail the probe — restarting web would not fix beat — so alert on the value.

The alerts above come from `apps/common/tasks.py` on the beat schedule. **Page** alerts are `ERROR` logs, which Sentry records as events; route on the message:

| Message | Task | Condition | Setting |
|---|---|---|---|
| `alert_stale_payments` | `ops.watch` (10 min) | more than N transactions still unverified 30 min after starting | `OPS_STALE_PAYMENT_ALERT` (5) |
| `alert_orders_stuck` | `ops.watch` | orders in `confirmed`/`preparing` longer than N minutes | `OPS_STUCK_ORDER_MINUTES` (60) |
| `alert_queue_depth` (warning) | `ops.watch` | Redis `celery` queue longer than N | `OPS_QUEUE_DEPTH_WARN` (100) |
| daily email | `ops.daily_report` | stuck orders, sent to the managers group and `OPS_ALERT_EMAILS` | — |

5xx rate, p95 latency, disk, pool and certificate alerts come from the platform and Sentry performance, not from code. After setting `SENTRY_DSN`, run `python manage.py sentry_check` and confirm the probe event arrives with its secrets redacted.

---

## 10. Rollback

1. Redeploy the previous image tag
2. If a migration must be reversed: `python manage.py migrate <app> <previous>` — **only** if the migration was written reversibly (NFR-11)
3. If data is corrupt: restore from PITR to just before the incident
4. Write an incident note: what, when, impact, cause, prevention

Payment reconciliation runs automatically after any rollback — orders paid during the incident window are settled by the beat task.

---

## Frontend ↔ API checklist

The frontend and API run on different origins. Every item below was found by running
them together; each fails silently or with an unhelpful error when wrong.

| Setting | Value | If wrong |
|---|---|---|
| `FRONTEND_URL` | `https://kuyashplace.com` | Email links and social error redirects point at the wrong site |
| `CORS_ALLOWED_ORIGINS` | the frontend origin | The browser blocks every API call |
| `CSRF_TRUSTED_ORIGINS` | the frontend origin | Every unsafe request fails CSRF; social sign-in rejects its `callback_url` |
| `SESSION_COOKIE_DOMAIN` | the shared parent, e.g. `.kuyashplace.com` | `proxy.ts` on the frontend never sees the session, so signed-in customers are sent to sign in again (`kuyash.E012`) |
| `GOOGLE_CLIENT_ID` / `_SECRET` | from the Google console | Blank: the Google button is hidden (by design) |
| `FACEBOOK_CLIENT_ID` / `_SECRET` | from the Facebook console | Blank: the Facebook button is hidden (by design) |
| OAuth redirect URIs in each console | `https://api.kuyashplace.com/accounts/<provider>/login/callback/` | The provider refuses the redirect |
| Frontend `NEXT_PUBLIC_API_URL` | `https://api.kuyashplace.com/api/v1`, set **before** `next build` | The value is baked into the bundle at build time |

`CORS_ALLOW_HEADERS` is not an environment setting: it is fixed in
`config/settings/base.py` to include `X-Cart-Token`, `X-Guest-Token` and
`Idempotency-Key`, and `apps/common/tests/test_cors.py` fails if any is removed.
