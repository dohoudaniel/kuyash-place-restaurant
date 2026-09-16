# Security & Compliance

---

## 1. Threat model

| Threat | Current exposure (frontend as-is) | Mitigation |
|---|---|---|
| **Price tampering** | **Total.** Every price, discount, VAT and fee is computed in the browser. Devtools sets any total to ₦0 | Server-authoritative pricing; `expected_total` guard; provider amount read from the persisted order |
| **Promo abuse** | **Total.** Codes and rules ship in the JS bundle; `usedCount` resets on refresh | Server-side codes, redemption ledger, per-user caps, rate-limited apply endpoint |
| **Payment forgery** | N/A today (no payments) — but the naive wiring is "client says success" | Webhook signature verification + server-side verification + amount matching |
| **Cardholder data breach** | **Imminent** — PAN/CVV collected in React state | Delete the form; hosted provider checkout only; CI grep gate |
| **Account takeover** | N/A (no accounts) | Argon2, rate limits, mandatory verification, session invalidation on password change |
| **Account enumeration** | N/A | Uniform responses on reset and registration |
| **IDOR on orders** | **Total** — `/orders/{anything}` returns data | UUID PKs, opaque references, object-level permissions, guest tokens |
| **Order enumeration** | **Total** — `Date.now()` references are guessable | Random 32⁶ reference space |
| **Spam / bot submissions** | **Total** — no protection on any form | Rate limits, honeypot, optional Turnstile |
| **XSS** | Moderate — React escapes by default | Nonce-based CSP with `'strict-dynamic'` (frontend `proxy.ts`); no `dangerouslySetInnerHTML` (policy pages render admin Markdown to React elements); HttpOnly session cookie |
| **CSRF** | N/A | Django CSRF + SameSite=Lax + explicit trusted origins |
| **Mass assignment** | N/A | Explicit serializer fields; price fields ignored on input |
| **DoS via expensive queries** | N/A | Pagination caps, query timeouts, Redis caching |

---

## 2. PCI-DSS posture

**Target: SAQ A** — the lightest tier, available to merchants who fully outsource cardholder data handling.

| Requirement | How we satisfy it |
|---|---|
| No storage of PAN | No such field exists in the schema |
| No storage of CVV | Prohibited by PCI-DSS Req. 3.2; no such field exists |
| No transmission through our servers | Hosted/inline provider checkout only |
| Payment page integrity | Provider-hosted; CSP restricts script sources |
| Provider is PCI-DSS Level 1 | Paystack and Flutterwave both are |
| Saved cards | Provider `authorization_code` tokens only, plus `last4`/`brand` for display |

**The single action that preserves this posture:** delete `cardNumber`, `cardName`, `cardExpiry` and `cardCvv` from `PaymentStep.tsx` and `PaymentStepCompact.tsx`. Connecting them instead moves the business to SAQ D — roughly 300 controls, annual assessment, and quarterly ASV scans.

CI gate (see `PAYMENTS.md` §1.1) fails the build if those identifiers reappear.

---

## 3. NDPR / data protection

Nigeria Data Protection Regulation obligations:

| Right | Implementation |
|---|---|
| Access | `GET /accounts/me/export/` returns a JSON archive of the user's data |
| Rectification | `PATCH /accounts/me/`, address CRUD |
| Erasure | `DELETE /accounts/me/` — **anonymises** rather than deletes: PII scrubbed, financial records retained 7 years for tax |
| Portability | Same JSON export |
| Consent | `marketing_opt_in` captured explicitly, withdrawable, one-click unsubscribe |
| Breach notification | Documented incident runbook; 72-hour notification |

**Data minimisation:** we do not collect date of birth unless the user opts into birthday rewards, and we never collect card data at all.

**Retention:** orders 7 years (tax); carts 30 days; anonymous sessions 14 days; webhook payloads 90 days; support tickets 2 years.

---

## 4. Application hardening checklist

```python
# config/settings/prod.py
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")          # never ["*"]

SECURE_SSL_REDIRECT           = True
SECURE_HSTS_SECONDS           = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS= True
SECURE_HSTS_PRELOAD           = True
SECURE_CONTENT_TYPE_NOSNIFF   = True
SECURE_REFERRER_POLICY        = "strict-origin-when-cross-origin"
SECURE_PROXY_SSL_HEADER       = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS               = "DENY"

SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher", ...]

DATA_UPLOAD_MAX_MEMORY_SIZE  = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500
```

Run `python manage.py check --deploy` in CI; the build fails on any warning.

### 4.1 Content Security Policy (frontend)

```
default-src 'self';
script-src  'self' https://js.paystack.co https://checkout.flutterwave.com;
frame-src   https://checkout.paystack.com https://checkout.flutterwave.com;
connect-src 'self' https://api.kuyashplace.com;
img-src     'self' data: https://<ref>.supabase.co;
style-src   'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src    https://fonts.gstatic.com;
object-src  'none'; base-uri 'self'; frame-ancestors 'none';
```

> Note `'unsafe-inline'` in `style-src` is currently **required** because the frontend uses 1,639 inline `style={{}}` attributes. Migrating those to Tailwind classes lets us drop it — a concrete security benefit from paying down that debt.

---

## 5. Secrets

| Secret | Storage |
|---|---|
| `DJANGO_SECRET_KEY` | Secret manager; rotated annually |
| `PAYSTACK_SECRET_KEY`, `FLUTTERWAVE_SECRET_KEY` | Secret manager; **never** `NEXT_PUBLIC_*` |
| `SUPABASE_S3_SECRET_KEY` | Secret manager |
| `DATABASE_URL` | Secret manager |
| Email provider key | Secret manager |

Rules: no secrets in the repo, in `next.config.ts`, or in any `NEXT_PUBLIC_` variable. `gitleaks` runs in CI. Any leaked key is rotated immediately, not "watched".

---

## 6. Logging and PII

**Never logged:** passwords, session keys, CSRF tokens, card data (which we never have), full addresses, `Authorization` headers, `guest_token`.

**Always logged:** request ID, user ID (not email), endpoint, status, duration, order reference, payment transaction ID.

Sentry: `send_default_pii=False`, with a `before_send` scrubber for `password`, `token`, `card`, `cvv`, `secret` and `authorization`.

---

## 7. Abuse prevention

| Vector | Control |
|---|---|
| Promo brute force | 10/min per cart; lockout after 20 failures/hour |
| Login brute force | 5/min per IP + 10/hour per email; `django-axes` on admin |
| Contact/catering spam | 3–5/hour per IP, honeypot field, optional Turnstile |
| Review spam | Verified purchase required + moderation queue |
| COD fraud | Order cap, verified account or prior delivery required |
| Order enumeration | Random references + object-level permissions |
| Scraping the menu | Public data; rate-limited, not blocked |

---

## 8. Pre-launch security gate

Phase 1 does not ship until every box is ticked:

- [x] Card fields deleted from the frontend; CI grep gate passing
- [x] `manage.py check --deploy` clean — at `--fail-level WARNING` with the real `config.settings.prod`, both in CI (Deployment check step) and in the suite (`common/tests/test_prod_settings.py`, which loads prod settings in a fresh interpreter). Re-run with the production environment's own values at deploy
- [x] `DEBUG = False`, `ALLOWED_HOSTS` explicit, HSTS on — `config/settings/prod.py`, proven by `common/tests/test_prod_settings.py`: DEBUG off, hosts exactly as configured (no default), HSTS one year with subdomains, SSL redirect, secure cookies, `X-Frame-Options: DENY`; a missing secret key, hosts, database or Redis URL stops the process
- [ ] All secrets in a secret manager; `gitleaks` clean on full history — *history clean*: gitleaks 8.28.0 over all 34 commits on 2026-09-15 found no leaks (and CI runs gitleaks on every push); no `.env` file was ever committed. Tick once production secrets live in the platform's secret store
- [x] Webhook signature verification tested against forged payloads — `payments/tests/test_webhooks.py` (forged, invalid and missing signatures rejected and recorded) and `test_webhook_edges.py` (replayed and concurrent duplicate deliveries)
- [x] Amount-mismatch path tested — order stays unpaid — `payments/tests/test_payment_flows.py` (mismatch record survives the raise; reconciliation survives a mismatch) and `test_webhooks.py` (logged as critical)
- [x] Idempotency verified under concurrent double-submit — `orders/tests/test_concurrency.py` (one Idempotency-Key admits one request; concurrent webhook deliveries settle once) and `test_orders_api.py` (double submit creates one order). The row-lock tests run in the CI Postgres job, which fails if any of them is skipped
- [x] Object-level permissions tested: user A cannot read user B's order — `orders/tests/test_orders_api.py`, `test_receipt.py`, `payments/tests/test_payments_api.py` and `test_saved_methods.py`, `accounts/tests/test_profile_and_addresses.py`, `reservations/tests/test_api.py`, plus the enrolment, review, chat and WebSocket suites (a stranger gets 404, never the object)
- [x] Rate limits verified on auth, promo and order endpoints — `accounts/tests/test_throttling.py` (login per IP and per email, registration, password reset, Retry-After) and `common/tests/test_scoped_throttles.py` (every scoped view installs the throttle; contact and order placement limited; reads don't spend the write allowance)
- [x] Per-IP limits cannot be dodged with a forged `X-Forwarded-For` — found 2026-09-14: DRF keyed anonymous throttles on the raw header and allauth trusted its leftmost entry, so a new made-up address per attempt meant the login limit never fired. All client-IP reads (DRF `NUM_PROXIES`, allauth's adapter, the admin allowlist, stored IPs) now go through `apps/common/client_ip.py`, which trusts only the entries appended by `TRUSTED_PROXY_COUNT` proxies. `kuyash.E021` warns when production sits behind a TLS proxy with a count of 0 (every visitor would share the proxy's address). Regression test: `common/tests/test_client_ip.py`
- [x] CSRF enforced on sign-in endpoints for anonymous visitors — login CSRF (`test_auth_hardening.py`)
- [x] Social sign-in failures and the takeover backstop return the browser to the frontend; no JSON or 500 on the provider callback
- [x] `next` / `callback_url` redirects restricted to same-site paths and trusted origins (no open redirect)
- [x] 2FA enabled on all staff and admin accounts — `apps/accounts/staff_mfa.py`: after the admin password, every staff session must pass an authenticator-app code (or a single-use recovery code) before any admin page; first sign-in forces enrolment with a QR code and ten recovery codes. Codes are replay-protected, five failures lock the step for 15 minutes, `next` cannot leave the admin, and the session key is cycled on success. Secrets are Fernet-encrypted at rest with a key derived from `SECRET_KEY` (`apps/accounts/mfa_adapter.py`) — **rotating `SECRET_KEY` makes every staff member re-enrol**. A superuser resets a lost phone from the Users admin ("Reset two-factor authentication"). `STAFF_MFA_REQUIRED=false` switches it off and trips `kuyash.W020` in the deploy check. Tests: `accounts/tests/test_staff_mfa.py`
- [ ] Admin behind IP allowlist / VPN on a non-default path — the non-default path is enforced by `kuyash.W019` in the deploy check (CI runs it with a non-default `ADMIN_URL`). An application-level allowlist is *implemented*: `ADMIN_ALLOWED_IPS` (addresses or CIDR ranges) answers 404 for the admin to everyone else, runs before sessions, and refuses to start on a malformed entry (`apps/common/client_ip.py`, `common/tests/test_client_ip.py`). Tick once production sets it (or a VPN/network allowlist is in place)
- [ ] CSP deployed and verified — *implemented*: nonce-based policy with `'strict-dynamic'` in `frontend/proxy.ts`, verified against `next start` (header on every page, a fresh nonce per request, every `<script>` carrying it, no `unsafe-eval`/`unsafe-inline` scripts). Tick after checking a real browser session on staging (sign-in including social, checkout redirect, map, live tracking) with no CSP violations in the console
- [ ] Automated backups running; **a restore actually tested** — *tooling implemented*: `scripts/backup-db.sh` and `scripts/restore-drill.sh`, which restores into an empty scratch database and runs `manage.py verify_restore` (migrations, order totals and lines, paid orders have payments, loyalty balances, staff 2FA secrets readable, freshness); CI runs the drill on every change. Tick once the platform's automated backups are on and a drill on staging data is recorded in `DEPLOYMENT.md` §8.2
- [ ] Sentry live with PII scrubbing confirmed — *scrubbing implemented and tested* (`send_default_pii=False`, `apps/common/observability.scrub_event`, `common/tests/test_observability.py`). Tick once a real DSN is set and `python manage.py sentry_check` shows its probe event with `password` and `card_number` redacted
- [x] `pip-audit` / `npm audit` clean of high and critical findings — clean of **all** known findings as of 2026-09-14: Django 5.2.6 → 5.2.17, DRF 3.16.1 → 3.17.2, django-allauth 65.11.2 → 65.14.1, Pillow 11.3.0 → 12.3.0, pytest 8.4.1 → 9.0.3; npm transitive fixes via `npm audit fix` (lockfile only). Re-run before launch — advisories keep arriving
- [ ] Tax policy (`PRD.md` §7) decided and the published copy corrected — enforced by `kuyash.E002`
- [ ] Terms, privacy and refund pages published — warned by `kuyash.W003`
- [ ] No menu item has `needs_repricing=True` — enforced by `kuyash.E001`
