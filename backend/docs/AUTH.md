# Authentication & Authorisation

**Decision:** django-allauth with **session cookies** (HttpOnly, Secure, SameSite=Lax). Social providers (Google, Facebook) in Phase 2.

---

## 1. Why sessions, not JWT in localStorage

The frontend currently has no auth at all, so we are choosing from a clean slate.

| | Session cookie (chosen) | JWT in `localStorage` |
|---|---|---|
| XSS token theft | **Impossible** — HttpOnly, JS cannot read it | Trivial — one XSS drains every session |
| Revocation | Immediate, server-side | Needs a blacklist, i.e. sessions with extra steps |
| CSRF | Needs handling — solved below | Not applicable |
| Complexity | Django does it | Rotation, refresh, expiry, storage, race conditions |
| Mobile app later | Add DRF token auth alongside | Already suited |

Given a browser-only product with real money in it, the XSS row decides it. A mobile app, if it ever arrives, gets a separate token-auth path without disturbing the web session.

---

## 2. Cookie and CORS configuration

The frontend and backend **must share a parent domain**. This is an infrastructure requirement, not a preference:

```
https://kuyashplace.com          → Next.js frontend
https://api.kuyashplace.com      → Django backend
```

```python
# config/settings/prod.py

SESSION_COOKIE_NAME     = "kuyash_session"
SESSION_COOKIE_HTTPONLY = True          # JS can never read it
SESSION_COOKIE_SECURE   = True          # HTTPS only
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN   = ".kuyashplace.com"
SESSION_COOKIE_AGE      = 60 * 60 * 24 * 14        # 14 days
SESSION_SAVE_EVERY_REQUEST = True                  # sliding expiry

CSRF_COOKIE_NAME     = "kuyash_csrftoken"
CSRF_COOKIE_HTTPONLY = False            # the frontend MUST read this one
CSRF_COOKIE_SECURE   = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_DOMAIN   = ".kuyashplace.com"
CSRF_TRUSTED_ORIGINS = ["https://kuyashplace.com", "https://www.kuyashplace.com"]

CORS_ALLOWED_ORIGINS   = ["https://kuyashplace.com", "https://www.kuyashplace.com"]
CORS_ALLOW_CREDENTIALS = True           # without this, cookies are not sent
```

> If Vercel preview deployments need access, add a regex origin **for staging only**. Never `CORS_ALLOW_ALL_ORIGINS = True` with `CORS_ALLOW_CREDENTIALS = True` — that combination is invalid and browsers reject it anyway.

### 2.1 Frontend contract

```ts
// every request
fetch(url, {
  credentials: "include",                       // non-negotiable
  headers: { "X-CSRFToken": getCookie("kuyash_csrftoken") },  // on unsafe methods
});
```

Call `GET /api/v1/auth/csrf/` once on app load to seed the CSRF cookie.

---

## 3. allauth configuration

```python
INSTALLED_APPS += [
    "allauth", "allauth.account", "allauth.headless",
    "allauth.socialaccount",                                  # Phase 2
    "allauth.socialaccount.providers.google",                 # Phase 2
    "allauth.socialaccount.providers.facebook",               # Phase 2
]

ACCOUNT_LOGIN_METHODS        = {"email"}          # no usernames — the UI has no such field
ACCOUNT_SIGNUP_FIELDS        = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION   = "mandatory"
ACCOUNT_CONFIRM_EMAIL_ON_GET = False              # GET must not mutate state
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_PASSWORD_MIN_LENGTH  = 10                 # UI currently claims 8 — update the copy
ACCOUNT_UNIQUE_EMAIL         = True
ACCOUNT_ADAPTER              = "apps.accounts.adapters.KuyashAccountAdapter"

# Throttled per IP *and* per account (AS-4). Replaces the deprecated
# ACCOUNT_LOGIN_ATTEMPTS_LIMIT / _TIMEOUT pair.
ACCOUNT_RATE_LIMITS = {
    "login_failed":  "5/5m/ip,10/h/key",
    "signup":        "3/h/ip",
    "reset_password":"3/h/ip,3/h/key",
}

PASSWORD_RESET_TIMEOUT = 3600                     # 1 hour — matches the existing UI copy
```

`allauth.headless` gives JSON endpoints for a decoupled frontend rather than Django's HTML views.

### 3.1 Custom adapter responsibilities

`apps/accounts/adapters.py`:

- Capture `full_name` and `phone` at signup (the current form collects both)
- Create a `Profile` and a `LoyaltyAccount` on registration
- Honour the `subscribeNewsletter` checkbox → `Profile.marketing_opt_in`
- **Claim guest orders**: on verification, attach any prior guest orders with the same email (AUTH-6)
- Send email through the `notifications` outbox so every send is recorded

---

## 4. Flows

### 4.1 Registration

```
POST /api/v1/auth/register/
  { email, password, full_name, phone, accept_terms, marketing_opt_in }
    │
    ├─ validate: password strength, email uniqueness, E.164 phone, terms accepted
    ├─ create User (is_email_verified=False) + Profile + LoyaltyAccount
    ├─ queue verification email (Celery)
    └─ 201 { "user": {...}, "email_verification_required": true }
          ↓
   User clicks the emailed link → frontend /verify-email?key=…
          ↓
POST /api/v1/auth/verify-email/ { key }
    ├─ mark verified, claim guest orders with this email
    └─ establish session → 200 { "user": {...} }
```

> `accept_terms` is validated **server-side**. The current UI enforces it with `alert("Please accept the terms and conditions")` — trivially bypassed and legally worthless.

### 4.2 Login

```
POST /api/v1/auth/login/ { email, password }
    ├─ rate limit: 5/min per IP, 10/hour per email
    ├─ authenticate
    ├─ if unverified → 403 { "code": "email_not_verified" }   (frontend offers resend)
    ├─ create session, set cookie
    ├─ merge the anonymous cart (X-Cart-Token) into the user cart
    └─ 200 { "user": {...} }
```

### 4.3 Password reset

Matches the promise the existing UI already prints on screen — *"The reset link will expire in 1 hour for security reasons"*:

```
POST /auth/password/reset/ { email }
    └─ 200 ALWAYS, whether or not the email exists      ← no account enumeration
       (queue email only if it does)

POST /auth/password/reset/confirm/ { uid, token, new_password }
    ├─ validate token (single-use, 1 hour)
    ├─ set password, invalidate ALL other sessions for that user
    └─ 200
```

### 4.4 Social login  *(Phase 2 — implemented)*

Wires up the two buttons that currently say `alert("Google login - Integration needed")`:

```
GET /api/v1/auth/social/google/  → 302 to Google
    └─ callback → allauth matches on verified email or creates a user
                → session established → redirect to the frontend
```

`SOCIALACCOUNT_EMAIL_AUTHENTICATION = True` only for providers that assert a **verified** email. Configured per provider in `SOCIALACCOUNT_PROVIDERS`: Google `EMAIL_AUTHENTICATION: True`, Facebook `False`.

`KuyashSocialAdapter.pre_social_login` is the backstop: if a provider claims an
address that already belongs to an account and has *not* verified it, the link
is refused with `409 social_email_unverified`. Without that check, anyone able
to create an account at a non-verifying provider could assert a victim's email
and be signed in as them.

Provider access tokens are not stored (`SOCIALACCOUNT_STORE_TOKENS = False`):
we never act on the customer's behalf at the provider, so retaining one would
be holding a credential with no purpose.

---

## 5. Guest checkout

The frontend allows checkout without an account today, and that behaviour is worth keeping.

- `POST /orders/` with a `guest` block creates an order with `user=null`
- The response includes a `guest_token`; `reference` + `guest_token` authorises `GET /orders/{ref}/` and cancellation
- The token is scoped to that one order, expires in 30 days, and grants nothing else
- On later registration with the same email, `claim_guest_orders()` attaches them

---

## 6. Authorisation model

Django `Group`s, not a `role` column — so a manager can also ride on a short-staffed evening.

| Group | Permissions |
|---|---|
| `customers` | Own cart, orders, addresses, reviews, reservations, loyalty |
| `kitchen` | `view_order`, `change_order_status`, `change_menuitem_availability` |
| `riders` | `view_assigned_order`, `change_delivery_assignment` |
| `managers` | Kitchen + rider + catalogue, pricing, promos, reservations, catering, refunds ≤ limit |
| `admin` | Django superuser |

### 6.1 Object-level ownership

```python
class IsOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        owner = getattr(obj, "user", None)
        if owner and owner == request.user:
            return True
        # guest access: reference + guest_token, constant-time compare
        token = request.headers.get("X-Guest-Token")
        return bool(token and constant_time_compare(token, getattr(obj, "guest_token", "")))
```

> Every `/orders/`, `/accounts/` and `/reservations/` object endpoint enforces this. Today `/account`, `/orders` and `/wishlist` are entirely public routes showing fabricated data.

### 6.2 Refund limits

`managers` may refund up to a configurable ceiling (default ₦50,000) per order; above that requires `admin`. Every refund records `initiated_by`.

---

## 7. Security requirements

| ID | Requirement |
|---|---|
| **AS-1** | Sessions invalidated on password change (all devices except the current one) |
| **AS-2** | Session rotated on privilege change |
| **AS-3** | Password reset never reveals whether an account exists |
| **AS-4** | Login throttled per IP **and** per email |
| **AS-5** | Email change requires re-verification; the old address is notified |
| **AS-6** | Staff accounts require 2FA (`django-otp`) before Phase 1 go-live |
| **AS-7** | Admin reachable only via allowlisted IPs or a VPN, on a non-default path |
| **AS-8** | All auth events written to an audit log |
| **AS-9** | Passwords hashed with Argon2 (`argon2-cffi`), not the PBKDF2 default |
| **AS-10** | `django-axes` for brute-force lockout on admin |

---

## 8. Frontend work required

| File | Change |
|---|---|
| `components/features/auth/LoginForm.tsx` | Delete `setTimeout` + `alert`. Call `POST /auth/login/`, handle `email_not_verified`, surface field errors |
| `components/features/auth/SignupForm.tsx` | Same. Replace the `<div onClick>` checkboxes with real `<input type="checkbox">` |
| `components/features/auth/ForgotPasswordForm.tsx` | Call the real endpoint; keep the existing success UI (it's good) |
| `components/features/auth/AuthModal.tsx` | Add `role="dialog"`, focus trap, Escape handling — or replace with `components/ui/dialog.tsx`, already installed |
| **new** `lib/store/authStore.ts` | Session state hydrated from `GET /auth/session/` |
| **new** `app/verify-email/page.tsx` | Handle the emailed verification link |
| **new** `app/reset-password/page.tsx` | Handle the emailed reset link |
| `components/layouts/navbar/Navbar.tsx` | Show the real user; add a logout control |
| `app/account/page.tsx`, `app/orders/`, `app/wishlist/` | Gate on auth; redirect unauthenticated visitors |
| `lib/api/client.ts` (new) | `credentials: "include"` + CSRF header on every request |

---

## Frontend integration: what the live run changed

Wiring the frontend to these endpoints (FRONTEND_INTEGRATION.md §5.2) surfaced
defects that only appear with a real browser on a different origin. The resulting
rules:

### CSRF on sign-in endpoints

DRF enforces CSRF only for requests it has authenticated from a session and treats
every other view as CSRF-exempt — which includes login, registration, email
verification, resend-verification, password reset and logout. Those endpoints also
accept form-encoded bodies, so a page on any site could post a login form and sign the
visitor into an attacker's account (login CSRF).

They now inherit `CsrfEnforcedMixin` (`apps/accounts/views.py`), which requires the
token on every unsafe request whether or not anyone is signed in. The frontend client
sends `X-CSRFToken` on every unsafe request and primes the cookie via
`GET /auth/csrf/` first, so it is unaffected. Regression: `test_auth_hardening.py`.

### Password reset signs the requester out

`confirm_password_reset` deletes every session for the user. When the visitor making
the request is signed in, that includes their own session, so the view now logs the
request out as well — otherwise the session middleware tries to save a deleted row
and a successful reset is reported as an HTML 400.

### Social sign-in

| Setting / route | Why it is required |
|---|---|
| `path("accounts/", include("allauth.urls"))` | Provider callbacks. Under `HEADLESS_ONLY` this exposes only those routes; without it every redirect raised `NoReverseMatch`. |
| `HEADLESS_FRONTEND_URLS["socialaccount_login_error"]` → `/auth/callback` | Where allauth sends a failed sign-in (cancelled, denied, provider error). Missing, every failure was a 500. |
| Frontend origin in `CSRF_TRUSTED_ORIGINS` | allauth accepts a `callback_url` only on a host from `ALLOWED_HOSTS` or `CSRF_TRUSTED_ORIGINS`. |
| Provider `APP` only when `*_CLIENT_ID` is set | allauth lists any provider with an `APP` entry, even a blank one; the frontend renders a button per listed provider. |

Register these callback URLs in the provider consoles, on the **API** origin:

```
https://api.kuyashplace.com/accounts/google/login/callback/
https://api.kuyashplace.com/accounts/facebook/login/callback/
```

The takeover backstop (§4.4) now answers a **browser** flow by redirecting to the
frontend callback with `?error=social_email_unverified` (keeping `next`), after
re-checking that the stored callback is a safe URL. Token flows, which have no
browser to redirect, keep the JSON 409.

Error codes the frontend's `/auth/callback` explains: `cancelled`, `denied`,
`unknown`, `signup_closed`, `permission_denied`, `reauthentication_required`,
`social_email_unverified`.
