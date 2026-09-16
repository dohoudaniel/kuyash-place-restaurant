# Setup

How to run Kuyash Place on your own machine, and what to set before deploying it anywhere else.

Two applications live in this repository:

| Folder | What it is | Runs on |
|---|---|---|
| `backend/` | Django 5 + DRF API, Django admin, Celery workers | `http://localhost:8000` |
| `frontend/` | Next.js 16 (App Router) customer site and kitchen screen | `http://localhost:3000` |

The frontend holds no business logic: prices, totals, availability and order state all come from the API. See [`API-DOCS.md`](API-DOCS.md) for the endpoints.

---

## 1. What you need

- **Python 3.12** and **Node.js 22** (the versions CI uses).
- **Git**.
- Nothing else. Local development needs **no Docker, no Postgres, no Redis**: it runs on SQLite, an in-memory cache and Celery executing tasks in-process ([`backend/docs/DECISIONS.md`](backend/docs/DECISIONS.md), ADR-015).

---

## 2. Backend

```bash
cd backend
make venv install            # .venv + runtime and dev dependencies
cp .env.example .env         # the defaults work as they are
make migrate seed            # SQLite schema, then the branch, hours, settings and role groups
.venv/bin/python manage.py createsuperuser
make run                     # http://localhost:8000
```

`make seed` also creates 18 menu items carrying the old prototype's prices. Every one is flagged `needs_repricing`, which **hides it from the public API** and fails `manage.py check --deploy` (`kuyash.E001`) until someone sets a real naira price in kobo. That is deliberate: launching with placeholder prices should be impossible.

| URL | What |
|---|---|
| `http://localhost:8000/api/v1/docs/` | Swagger UI — every endpoint, try-it-out included |
| `http://localhost:8000/api/v1/redoc/` | The same schema, ReDoc layout |
| `http://localhost:8000/api/v1/schema/` | The OpenAPI document itself (3.0.3) |
| `http://localhost:8000/admin/` | Django admin (staff) |
| `http://localhost:8000/health/` | Database, cache and scheduler status |

**The admin asks for a second factor.** `STAFF_MFA_REQUIRED` defaults to on, so the first admin sign-in shows a QR code to scan with an authenticator app, then ten recovery codes. To skip it while developing locally, set `STAFF_MFA_REQUIRED=false` in `backend/.env` — never in a deployed environment (the deploy check warns with `kuyash.W020`).

### Logs

Development writes to the terminal **and** to `backend/logs/kuyash.log`, because the terminal scrolls away and "what happened in that request ten minutes ago" is the most common local question.

```bash
make logs                                   # follow it
jq -r 'select(.levelname != "INFO")' logs/kuyash.log     # only warnings and worse
jq -r 'select(.request_id == "<id>")' logs/kuyash.log    # one request, end to end
```

The file is JSON, one object per line, and every line carries a `request_id`: the API returns that same id in the `X-Request-ID` response header, so you can take an id from a failing call and pull out everything it did. It rotates at 5 MB, keeps five files, and `logs/` is git-ignored.

To switch it off, or move it, set `LOG_DIR=` (or a path) in `backend/.env`. **Deployed environments leave `LOG_DIR` unset** and log JSON to stdout for the platform to collect — a file inside a container is lost on the next deploy and can fill the disk.

### Optional services

Everything works without these; add them when you want to exercise the real thing.

| Want | Set in `backend/.env` |
|---|---|
| Postgres instead of SQLite | `DATABASE_URL=postgres://user:pass@localhost:5432/kuyash` |
| Real background workers and WebSockets across processes | `REDIS_URL=redis://localhost:6379/0` and `CELERY_TASK_ALWAYS_EAGER=False`, then run `celery -A config worker -l info` and `celery -A config beat -l info` |
| Card payments end to end | `PAYSTACK_SECRET_KEY` (test key) and `PAYMENT_CALLBACK_URL` |
| Uploads on Supabase rather than local disk | the `SUPABASE_*` values |
| Google or Facebook sign-in | `GOOGLE_CLIENT_ID` / `FACEBOOK_CLIENT_ID` and their secrets |

With no payment key and `DEBUG=True`, checkout uses a built-in simulator so the whole purchase path can be walked offline. Emails are printed to the console and stored in the notifications outbox, so verification links are always recoverable.

---

## 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev                  # http://localhost:3000
```

`NEXT_PUBLIC_API_URL` is baked into the browser bundle at build time, so it must be right **before** `npm run build`, not just at runtime.

| Command | What it does |
|---|---|
| `npm run dev` | Development server (webpack, not turbopack) |
| `npm run build` / `npm run start` | Production build and server |
| `npm run lint` | ESLint — currently clean, keep it that way |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run api:sync` | Regenerate `lib/api/openapi.yml` and `lib/api/schema.d.ts` from the running code |

**Run `npm run api:sync` whenever a backend serializer, view or URL changes.** It regenerates the OpenAPI document and the TypeScript types from it; never hand-edit `lib/api/schema.d.ts`. There is no frontend test runner.

### The kitchen screen

`/kitchen` is the Kitchen Display System. It needs an account in the **kitchen** or **managers** group: in the admin, open *Users → the person → Groups → kitchen → Save*. Anyone else sees "Kitchen staff only". The staff guide is [`backend/docs/KDS_GUIDE.md`](backend/docs/KDS_GUIDE.md).

---

## 4. Everyday commands (backend)

```bash
make test          # pytest
make lint          # ruff
make typecheck     # mypy
make coverage      # 85% overall, 100% on every money path
make check         # what CI runs
```

Other useful ones:

```bash
.venv/bin/python manage.py launch_status        # what still stands between this environment and launch
.venv/bin/python manage.py check --deploy       # project checks (kuyash.E*/W*)
.venv/bin/python manage.py seed_initial         # idempotent; safe to re-run
.venv/bin/python manage.py verify_restore       # integrity of a restored database
.venv/bin/python manage.py sentry_check         # send a scrubbed test event (needs SENTRY_DSN)
./scripts/backup-db.sh                          # Postgres dump + checksum
./scripts/restore-drill.sh <dump> <scratch URL> # restore into an empty database and verify it
```

Three grep gates guard the frontend and also run in CI:

```bash
./scripts/check-no-card-fields.sh        # no card number, CVV or expiry fields anywhere
./scripts/check-no-price-arithmetic.sh   # components render Money.display, never compute totals
./scripts/check-no-alert.sh              # no alert()/window.confirm() standing in for a real result
```

---

## 5. Signing in as a customer locally

1. Register at `http://localhost:3000` (sign-up needs a name, email, phone and accepting the terms).
2. The verification email is printed in the backend console — open the link, or find the body in the admin under *Notifications*.
3. You are signed in once the address is verified. Email verification is mandatory here, exactly as in production.

---

## 6. Environment variables

`backend/.env.example` documents every variable with its default. The ones that matter most outside local development:

| Variable | Why it matters |
|---|---|
| `DJANGO_SECRET_KEY` | 50+ random characters. **Rotating it forces every staff member to re-enrol their authenticator app.** |
| `ALLOWED_HOSTS` | Explicit hostnames; production refuses to start without it |
| `DATABASE_URL`, `REDIS_URL` | Both required in production |
| `SESSION_COOKIE_DOMAIN` | The shared parent domain (`.kuyashplace.com`), or the frontend cannot hold a session |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | The frontend's exact origin |
| `TRUSTED_PROXY_COUNT` | Number of proxies in front of Django. `0` behind a proxy puts every visitor on one IP, so one person's failed logins throttle everyone |
| `ADMIN_URL` | A non-guessable admin path |
| `ADMIN_ALLOWED_IPS` | Optional allowlist; everyone else gets a 404 for the admin |
| `PAYSTACK_SECRET_KEY` / `FLUTTERWAVE_SECRET_KEY` | At least one, or the app refuses to start in production |
| `PAYMENT_CALLBACK_URL`, `ACADEMY_PAYMENT_CALLBACK_URL` | Must be `https://` |
| `SENTRY_DSN` | Error reporting; then run `manage.py sentry_check` |
| `STAFF_MFA_REQUIRED` | Keep it on outside local development |

Deploying is covered separately in [`backend/docs/DEPLOYMENT.md`](backend/docs/DEPLOYMENT.md) (Daphne, Celery, Redis, backups, monitoring). Before going live, run `manage.py launch_status` in the target environment and work through what it lists.

---

## 7. When something is wrong

| Symptom | Cause and fix |
|---|---|
| Frontend shows "network error" everywhere | The backend isn't running, or `NEXT_PUBLIC_API_URL` is wrong. It must include `/api/v1` |
| Signed in but the session is lost on refresh | The API origin and the site origin disagree. Check `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`; in production also `SESSION_COOKIE_DOMAIN` |
| `403` with `permission_denied` on a write | The CSRF token is missing or stale. Call `GET /api/v1/auth/csrf/` first, then echo the `kuyash_csrftoken` cookie back as `X-CSRFToken` |
| A dish is missing from the menu | It is still flagged `needs_repricing`, is marked sold out, or sits outside its availability window |
| The admin asks for a code you don't have | Two-factor is on. Enrol with an authenticator app, or set `STAFF_MFA_REQUIRED=false` locally |
| Order status never changes on `/orders/{ref}` | The live socket is unavailable and polling is covering; check `REDIS_URL` in production. Locally, `make run` serves WebSockets in the same process |
| Types out of step with the API | `npm run api:sync` |
| Emails never arrive locally | They are meant to print to the console; the outbox in the admin holds every message |
| Nothing in `logs/kuyash.log` | Only development writes it, and only once something is logged. Check `LOG_DIR` in `backend/.env` |

---

## 8. Where to read next

| Document | For |
|---|---|
| [`API-DOCS.md`](API-DOCS.md) | Every endpoint and how to call it |
| [`backend/README.md`](backend/README.md) | The backend's rules and the repricing gate |
| [`backend/docs/ARCHITECTURE.md`](backend/docs/ARCHITECTURE.md) | How the apps fit together |
| [`backend/docs/DEPLOYMENT.md`](backend/docs/DEPLOYMENT.md) | Deploying, backups, monitoring |
| [`backend/docs/SECURITY.md`](backend/docs/SECURITY.md) | The security checklist |
| [`backend/docs/TESTING.md`](backend/docs/TESTING.md) | How tests are organised, especially money tests |
| [`backend/docs/KDS_GUIDE.md`](backend/docs/KDS_GUIDE.md) | The kitchen screen, for staff |
