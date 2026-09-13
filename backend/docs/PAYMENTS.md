# Payments

**Providers:** Paystack (primary) · Flutterwave (secondary) · bank transfer · cash on delivery
**Currency:** NGN only · **all amounts integer kobo**

---

## 1. The rule that overrides everything

> ### The existing card form must be DELETED, not connected.

`frontend/components/features/checkout/PaymentStep.tsx` and `PaymentStepCompact.tsx` currently collect:

```tsx
const [formData, setFormData] = useState<PaymentData>({
  method: "card",
  cardNumber: "",      // ❌ full PAN
  cardName: "",        // ❌
  cardExpiry: "",      // ❌
  cardCvv: "",         // ❌ CVV — storage prohibited outright by PCI-DSS Req. 3.2
});
```

Today this is a dark pattern: the data is collected and thrown away. **The danger is the obvious next step.** The moment anyone posts that object to a Django endpoint, Kuyash Place is:

- **transmitting and processing raw cardholder data** → PCI-DSS **SAQ D**, the most demanding self-assessment tier (~300 controls), instead of **SAQ A** (~30) which hosted checkout qualifies for
- exposed to card-brand fines and potential loss of merchant facilities
- logging PANs into Django request logs, Sentry breadcrumbs and Postgres query logs, almost certainly by accident

**There is no field anywhere in the data model or API for a card number.** That is deliberate and permanent.

### 1.1 Enforcement

Two complementary checks, split by what each can actually see.

**Backend — AST analysis**, in `apps/payments/tests/test_no_card_data.py`:

- no model field on any payments model may be named for a PAN, CVV or expiry;
- no serializer may declare such a field, so no request body can carry one in;
- no source file in the package may *reference* such an identifier.

It walks the syntax tree rather than the text, which is what lets it tell a real
field from a docstring saying "there is no CVV field here", or from a test whose
whole purpose is to post card fields and assert they are discarded. A text scan
flagged all three, and the fix would have been an ever-growing exclusion list.

**Frontend — text scan**, in `backend/scripts/check-no-card-fields.sh`, because
no AST tooling is readily at hand for the TypeScript side. A hit is a hard
failure except for an explicit allowlist of the five pre-existing files
scheduled for Phase 1 deletion; that list may only shrink.

Sketch of the frontend scan:

```bash
# scripts/check-no-card-fields.sh
if grep -rniE 'cardNumber|cardCvv|cardExpiry|card_number|card_cvv|\bcvv\b|\bpan\b' \
     frontend/ backend/ --include='*.ts' --include='*.tsx' --include='*.py' \
     | grep -v 'card_last4\|card_brand\|card_exp_month\|card_exp_year\|PAYMENTS.md\|FRONTEND_AUDIT.md'; then
  echo "❌ Card data fields detected. Payments must use hosted provider checkout."
  exit 1
fi
```

---

## 2. The model: hosted / inline checkout

```
Browser                    Django                        Paystack
   │                         │                              │
   │─ POST /orders/ ────────▶│                              │
   │                         │─ initialise(amount, email) ─▶│
   │                         │◀──── authorization_url ──────│
   │◀── 201 + auth_url ──────│                              │
   │                         │                              │
   │═══════ redirect / inline popup ══════════════════════▶│
   │                                                        │
   │        CARD DATA GOES HERE — NEVER TO US               │
   │                                                        │
   │◀════════ redirect back to /checkout/complete ══════════│
   │                         │                              │
   │─ GET /payments/verify/ ▶│─── verify(reference) ───────▶│
   │                         │◀──── status: success ────────│
   │◀── order: paid ─────────│                              │
   │                         │                              │
   │                         │◀═══ POST /webhooks/paystack/ │  ← THE authority
   │                         │     (signature verified)     │
```

We hold: an amount, an email, a reference, and afterwards a `last4`/`brand` for display. Nothing else.

---

## 3. Verification — never trust the client

**PAY-3 is the rule that prevents free food.**

A malicious customer can call the frontend's success callback directly. The naive implementation — "the browser came back from Paystack, so mark it paid" — hands out free orders to anyone who reads the network tab.

An order becomes `paid` **only** when:

1. A **signature-verified webhook** arrives and the amount and currency match the order, **or**
2. A **server-to-server verification call** to the provider confirms it.

The browser's return from the provider is a *hint to verify*, never proof.

```python
# apps/payments/services/verification.py
def verify_and_settle(txn: PaymentTransaction) -> PaymentTransaction:
    provider = get_provider(txn.provider)
    result = provider.verify(txn.provider_reference)          # server → provider

    if result.status != "success":
        txn.status = "failed"; txn.failure_reason = result.message
        txn.save(); return txn

    # PAY-5 — an amount mismatch is a security event, not a rounding issue
    if result.amount_kobo != txn.amount or result.currency != "NGN":
        logger.critical("payment_amount_mismatch", extra={
            "txn": str(txn.id), "expected": txn.amount, "got": result.amount_kobo})
        txn.status = "failed"; txn.failure_reason = "amount_mismatch"
        txn.save()
        raise PaymentAmountMismatch(txn)                       # order stays UNPAID

    with transaction.atomic():
        txn.status = "success"
        txn.amount_verified = result.amount_kobo
        txn.channel = result.channel
        txn.card_last4 = result.last4
        txn.card_brand = result.brand
        txn.authorization_code = result.authorization_code     # token only, never a PAN
        txn.verified_at = timezone.now()
        txn.save()
        orders.services.mark_paid(txn.order, source="webhook")
    return txn
```

---

## 4. Webhooks

### 4.1 Signature verification

**Paystack** — HMAC-SHA512 of the raw body with the secret key, compared to `x-paystack-signature`:

```python
@csrf_exempt
@require_POST
def paystack_webhook(request):
    raw = request.body                                  # RAW bytes — never the parsed dict
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(),
                        raw, hashlib.sha512).hexdigest()
    got = request.headers.get("x-paystack-signature", "")
    if not hmac.compare_digest(expected, got):          # constant-time
        WebhookEvent.objects.create(provider="paystack", signature_valid=False,
                                    payload=json.loads(raw or b"{}"))
        return HttpResponse(status=401)
    ...
```

**Flutterwave** — compare the `verif-hash` header to the configured secret hash with `hmac.compare_digest`.

### 4.2 Idempotency

Providers retry. Duplicate delivery must not double-credit:

```python
event_id = payload.get("id") or payload.get("data", {}).get("id")
event, created = WebhookEvent.objects.get_or_create(
    provider="paystack", event_id=str(event_id),
    defaults={"event_type": payload.get("event"), "payload": payload, "signature_valid": True},
)
if not created and event.processed_at:
    return HttpResponse(status=200)        # already handled — ack and stop
```

`WebhookEvent.event_id` is **unique**. That constraint is the idempotency guard.

### 4.3 Rules

| ID | Rule |
|---|---|
| WH-1 | Verify the signature against the **raw body** before parsing |
| WH-2 | Persist every event, valid or not, before processing |
| WH-3 | Return `200` fast; do the work in Celery if it is slow |
| WH-4 | Never trust amounts in the payload — re-verify against the provider API |
| WH-5 | Webhook URLs are `csrf_exempt` and **unauthenticated by design** — the signature is the authentication |
| WH-6 | Log and alert on any invalid signature; repeated failures may be an attack |
| WH-7 | Unhandled event types are acked and ignored, never 500'd |

### 4.4 The reconciliation safety net

Webhooks fail. The endpoint is down, DNS breaks, the provider has an incident — and money has changed hands.

```python
@shared_task
def verify_pending_payments():
    """Beat: every 10 minutes."""
    cutoff = timezone.now() - timedelta(minutes=5)
    stale = PaymentTransaction.objects.filter(
        status__in=["initialised", "pending"], initialised_at__lt=cutoff,
    ).exclude(initialised_at__lt=timezone.now() - timedelta(hours=24))
    for txn in stale:
        try:
            verify_and_settle(txn)
        except Exception:
            logger.exception("reconciliation_failed", extra={"txn": str(txn.id)})
```

**This task is not optional.** It is the difference between "a customer paid and never got their food" and "the system healed itself in under ten minutes."

---

## 5. Payment methods

### 5.1 Card — Paystack / Flutterwave

```
POST /payments/initialise/  { "order": "KYS-7Q2XF9", "provider": "paystack", "save_card": false }
  → { "authorization_url": "https://checkout.paystack.com/…", "reference": "KYS-7Q2XF9-1", "amount": { … } }
```

`save_card` is the customer's consent to keep the card for next time. It defaults
to `false`, and without it no provider token is stored — even though the provider
returns one on every successful card payment. Until the frontend integration pass
the serializer did not declare this field, so the view read a key validation had
already dropped and consent could never be given; the saved-card tests had set the
model flag directly and did not notice. It is now covered through the endpoint.

Amount sent in kobo. `callback_url` returns the browser to `/checkout/complete?reference=…`, which triggers verification.

Provider choice: default Paystack; fall back to Flutterwave on initialise failure; managers can flip the default in admin. Both live behind one interface:

```python
class PaymentProvider(Protocol):
    def initialise(self, *, amount_kobo: int, email: str, reference: str,
                   callback_url: str, metadata: dict) -> InitResult: ...
    def verify(self, reference: str) -> VerifyResult: ...
    def refund(self, reference: str, amount_kobo: int | None) -> RefundResult: ...
    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> bool: ...
```

Adding a third provider is a new class, not a new branch in the order service.

In development, with no provider keys and `DEBUG` on, the simulated provider returns a
checkout URL pointing straight back at `/checkout/complete`, and verifies using the
amount recorded for that transaction. It used to verify every payment as ₦0, which
settlement correctly rejects as an amount mismatch — so the checkout could not be
walked end to end locally. It is refused outright when `DEBUG` is off.

### 5.2 Bank transfer

> **Status (frontend integration):** implemented as `Branch.bank_name`,
> `bank_account_name` and `bank_account_number`, published as `bank_transfer` on
> `/core/branch/`. With any field blank the checkout hides the option **and**
> placement refuses it — an order placed for transfer with no account to pay into can
> never be paid. The checkout previously promised details that did not exist.

Order created `pending_payment`; API returns the account details that were hardcoded in the frontend's `PaymentStepCompact.tsx` (since deleted) — **now served from `Branch`, so they can be changed without a deploy.** Staff confirm receipt in admin, which transitions the order and writes a `PaymentTransaction(provider="bank_transfer")`.

> Phase 3 upgrade: a dedicated virtual account per order (both providers support this) for automatic reconciliation.

### 5.3 Cash on delivery

> **Status:** the cap and the verified-account requirement below are **not enforced**
> by `place_order` today — cash orders are accepted and confirmed immediately. Open
> decision OD-8 in DECISIONS.md.

Order created `confirmed` with `payment_status="unpaid"`. `DeliveryAssignment.cash_collected` records what the rider took; a shift-end reconciliation report flags shortfalls. COD carries fraud risk, so it is gated on: order total below a configurable cap, and either a verified account or a previously delivered order.

### 5.4 Tips

The current tip UI offers **₦2 / ₦5 / ₦10** — dollar amounts with a naira glyph. Backend stores tips in kobo; the **presets must be repriced** (suggest ₦200 / ₦500 / ₦1,000 plus a custom field). Tips are added to the charge, tracked separately for staff distribution, and excluded from VAT.

---

## 6. Refunds

| ID | Rule |
|---|---|
| RF-1 | Full and partial refunds supported through the provider API |
| RF-2 | Every refund recorded with amount, reason and `initiated_by` |
| RF-3 | A refund **reverses loyalty points** (`PointsLedgerEntry` type `reversal`) |
| RF-4 | A refund **reverses the promo redemption**, restoring the customer's remaining uses |
| RF-5 | Order rejection by the kitchen **auto-refunds** prepaid orders |
| RF-6 | Managers may refund up to a ceiling (default ₦50,000); above that requires admin |
| RF-7 | COD refunds are recorded as manual/cash and reconciled offline |
| RF-8 | Refund webhooks update the transaction and order `payment_status` |

---

## 7. Money handling rules

Restating, because this is where the current frontend is most wrong.

| ID | Rule |
|---|---|
| M-1 | All money is **integer kobo**. ₦1,250.00 → `125000` |
| M-2 | **`float` is banned** in every money path. `Decimal` for intermediates, rounded to int immediately |
| M-3 | Rounding is `ROUND_HALF_UP`, applied **once per component**, never accumulated |
| M-4 | VAT is computed **per line** by `tax_class`, then summed — never applied to the order subtotal |
| M-5 | Totals are recomputed at order placement, not carried from the cart |
| M-6 | The amount sent to the provider is read from the persisted `Order`, never from a request body |
| M-7 | The verified amount is checked against the order total; a mismatch blocks settlement |
| M-8 | The API returns `{amount, currency, display}`; the frontend **never formats currency** |
| M-9 | Every money mutation is recorded — no in-place edits without an audit row |

### 7.1 Worked example — VAT-inclusive (Option A, default)

```
Line 1  Signature Grill Plate (Large) ×2
        base 1,490,000 + variant 300,000 + extras 50,000 = 1,840,000/unit
        line_subtotal                                    = 3,680,000
Subtotal                                                 = 3,680,000
Promo WELCOME10 (10%, capped ₦5,000)                     =  -368,000
Delivery (VI ₦1,500, waived — over ₦15,000 threshold)    =         0
Tip                                                      =         0
────────────────────────────────────────────────────────────────────
Grand total (what the customer pays)                     = 3,312,000   ₦33,120.00
VAT included, extracted for accounting:
  3,312,000 × 7.5 / 107.5 = 231,069.767… → ROUND_HALF_UP → 231,070     ₦2,310.70
Net of VAT                                               = 3,080,930
```

The customer pays exactly the menu price. **No surprise at checkout** — which is also what the published terms already promise.

---

## 8. Configuration

```bash
PAYSTACK_SECRET_KEY=sk_live_xxx          # server only — NEVER exposed
PAYSTACK_PUBLIC_KEY=pk_live_xxx          # safe for the browser (inline checkout)
PAYSTACK_WEBHOOK_ALLOWLIST=...           # optional IP allowlist

FLUTTERWAVE_SECRET_KEY=FLWSECK-xxx
FLUTTERWAVE_PUBLIC_KEY=FLWPUBK-xxx
FLUTTERWAVE_ENCRYPTION_KEY=xxx
FLUTTERWAVE_WEBHOOK_SECRET_HASH=xxx

DEFAULT_PAYMENT_PROVIDER=paystack
PAYMENT_CALLBACK_URL=https://kuyashplace.com/checkout/complete
```

Secret keys live in the secret manager, never in the repo, never in `NEXT_PUBLIC_*`.

---

## 9. Testing — non-negotiable

Per NFR-8, **100% coverage** on this module.

| Test | Asserts |
|---|---|
| Webhook with a bad signature | 401, order unchanged |
| Webhook replayed twice | Processed once, second acked |
| Webhook amount < order total | Order stays unpaid, critical alert raised |
| Webhook for an unknown reference | 200, logged, no crash |
| Client calls verify with a forged reference | No state change |
| Provider timeout on initialise | Order stays `pending_payment`, retry available |
| Provider timeout on verify | Left pending; reconciliation resolves it |
| Reconciliation catches a missed webhook | Order transitions to `paid` |
| Double-tap order creation | One order, one charge (idempotency) |
| Refund | Points reversed, promo redemption reversed |
| Partial refund | `payment_status = partially_refunded` |
| Every VAT calculation | Exact kobo, both directions, including zero-rated lines |
| Percentage discount with a cap | Cap respected to the kobo |
| `float` anywhere in the money path | Static check fails the build |

Provider sandboxes are used in CI via recorded fixtures (`responses`/`vcrpy`); no live keys in tests.
