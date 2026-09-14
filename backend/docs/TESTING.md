# Testing Strategy

**Target:** ≥ 85% overall · **100% on money, tax, discount, payment and state-machine logic** (NFR-8)

**Stack:** pytest · pytest-django · factory-boy · responses/vcrpy · pytest-cov

---

## 1. The rule

> Any code path that can change how much a customer is charged has **100% branch coverage**, or it does not merge.

That covers: `apps/common/money.py`, `apps/carts/services/pricing.py`, `apps/promotions/services/`, `apps/payments/services/`, `apps/orders/services/state.py`, `apps/delivery/services/zones.py`.

CI enforces it per-module, not just globally — an 85% overall figure can hide a 40% pricing module.

---

## 2. Test pyramid

| Layer | Share | What |
|---|---|---|
| Unit | 60% | Pure functions: money, VAT, discounts, ETA, state transitions. No database. |
| Integration | 30% | Services against a real Postgres: cart repricing, order placement, webhooks |
| API | 10% | Endpoint contracts: status codes, permissions, error shapes |
| E2E | a handful | Full checkout against provider sandboxes |

---

## 3. The money tests (non-negotiable)

```python
@pytest.mark.parametrize("gross,expected_vat", [
    (0, 0),
    (100, 7),               # ₦1.00 → 6.97…k → ROUND_HALF_UP → 7k
    (107_50, 750),
    (3_312_000, 231_070),   # the PRD worked example
    (1, 0),                 # sub-kobo rounds to zero, never negative
])
def test_vat_inclusive_extraction(gross, expected_vat):
    assert extract_vat(gross, rate_bps=750) == expected_vat


def test_vat_is_summed_per_line_not_applied_to_subtotal():
    """A zero-rated line must not attract VAT via the order subtotal."""
    lines = [Line(amount=100_000, tax_class="standard"),
             Line(amount=100_000, tax_class="zero_rated")]
    assert compute_vat(lines, rate_bps=750) == extract_vat(100_000, 750)


def test_percentage_discount_respects_cap_to_the_kobo():
    promo = PromoCodeFactory(discount_type="percentage", value=1000,       # 10%
                             max_discount=500_000)                          # ₦5,000
    assert calculate_discount(promo, subtotal=10_000_000) == 500_000


def test_rounding_applied_once_not_accumulated():
    """Three lines of ₦3.33 must total ₦9.99, never ₦10.00."""
    assert compute_total([333, 333, 333]) == 999


def test_no_binary_floating_point_in_the_money_path():
    """Structural guard: the money module must never reference Python's float.

    An AST check, not a substring search. The original substring version was
    wrong in both directions: it failed on a docstring that merely mentioned the
    word, and it would have passed `eval("float")`.
    """
    tree = ast.parse(Path("apps/common/money.py").read_text())
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "float" not in names and "float" not in attrs
    assert not [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, float)
    ]
```

### 3.1 The regression tests for the audit findings

Each of these encodes a specific bug found in the frontend, so it can never reappear server-side:

```python
def test_server_ignores_client_supplied_price():
    """Frontend bug: prices were client-computed. Server must ignore them entirely."""
    res = api.post("/cart/items/", {"menu_item": "burger", "quantity": 1, "price": 1})
    assert res.json()["items"][0]["unit_price"]["amount"] == MenuItem.objects.get(slug="burger").base_price


def test_order_rejects_mismatched_expected_total():
    """Price changed between cart read and order placement."""
    cart = make_cart(total=3_312_000)
    MenuItem.objects.filter(slug="burger").update(base_price=F("base_price") + 100_000)
    res = api.post("/orders/", {"expected_total": 3_312_000, ...})
    assert res.status_code == 409 and res.json()["code"] == "price_changed"


def test_cart_not_cleared_until_payment_verified():
    """Frontend bug: cart was cleared before anything persisted."""
    order = place_order(cart)
    assert cart.items.exists()                     # still there
    settle_payment(order)
    assert not cart.refresh().items.exists()       # now cleared


def test_promo_usage_limit_is_enforced_across_requests():
    """Frontend bug: usedCount reset on page refresh."""
    promo = PromoCodeFactory(usage_limit=1)
    assert apply_promo(promo, cart_a).success
    confirm_redemption(promo, order_a)
    assert not apply_promo(promo, cart_b).success


def test_item_id_is_stable_across_rename():
    """Frontend bug: item ID derived from imageKey/name slug."""
    item = MenuItemFactory(slug="classic-smash-burger")
    cart_item = add_to_cart(item)
    item.name = "The Smash"; item.save()
    assert cart_item.refresh().menu_item_id == item.id
```

---

## 4. Payment tests

```python
def test_webhook_rejects_forged_signature():
    res = client.post("/api/v1/webhooks/paystack/", data=payload,
                      HTTP_X_PAYSTACK_SIGNATURE="deadbeef")
    assert res.status_code == 401
    assert order.refresh().status == "pending_payment"       # unchanged


def test_webhook_is_idempotent_on_replay():
    send_webhook(payload); send_webhook(payload)             # identical event id
    assert PaymentTransaction.objects.filter(order=order, status="success").count() == 1
    assert OrderStatusEvent.objects.filter(order=order, to_status="paid").count() == 1


def test_amount_mismatch_never_marks_order_paid():
    """Customer pays ₦100 for a ₦33,120 order."""
    send_webhook(payload_with_amount(10_000))
    assert order.refresh().payment_status == "unpaid"
    assert "payment_amount_mismatch" in caplog.text


def test_client_cannot_mark_order_paid():
    res = api.get(f"/payments/verify/{order.reference}/")     # provider says failed
    assert order.refresh().status == "pending_payment"


def test_reconciliation_settles_a_missed_webhook():
    txn = PaymentTransactionFactory(status="pending",
                                    initialised_at=now() - timedelta(minutes=10))
    with mock_provider_verify(status="success", amount=txn.amount):
        verify_pending_payments()
    assert txn.refresh().status == "success"
    assert txn.order.refresh().status == "paid"


def test_double_submit_creates_one_order_and_one_charge():
    key = str(uuid4())
    r1 = api.post("/orders/", body, HTTP_IDEMPOTENCY_KEY=key)
    r2 = api.post("/orders/", body, HTTP_IDEMPOTENCY_KEY=key)
    assert r1.json()["reference"] == r2.json()["reference"]
    assert Order.objects.count() == 1
```

Provider calls are replayed from recorded fixtures. **No live keys in CI.**

---

## 5. State machine tests

```python
@pytest.mark.parametrize("frm,to,legal", [
    ("pending_payment", "paid", True),
    ("pending_payment", "delivered", False),      # no skipping
    ("delivered", "preparing", False),            # no going back
    ("refunded", "paid", False),                  # terminal
])
def test_transition_legality(frm, to, legal): ...


def test_concurrent_accept_produces_one_transition():
    """Two staff tap Accept simultaneously."""
    with ThreadPoolExecutor(2) as ex:
        results = [f for f in ex.map(lambda _: try_accept(order), range(2))]
    assert sum(r.ok for r in results) == 1
    assert OrderStatusEvent.objects.filter(order=order, to_status="confirmed").count() == 1


def test_kitchen_cannot_refund():
    with pytest.raises(PermissionDenied):
        transition(order, "refunded", actor=kitchen_user)
```

---

## 6. Permission tests

```python
def test_user_cannot_read_another_users_order():
    assert api.as_(user_b).get(f"/orders/{order_of_a.reference}/").status_code == 404


def test_guest_token_scoped_to_one_order():
    assert api.get(f"/orders/{other.reference}/",
                   HTTP_X_GUEST_TOKEN=token_for_order_a).status_code == 404


def test_order_references_are_not_enumerable():
    refs = [generate_reference() for _ in range(1000)]
    assert len(set(refs)) == 1000
    assert not any(is_sequential(a, b) for a, b in pairwise(refs))
```

---

## 7. Reservation concurrency (Phase 2)

```python
def test_double_booking_is_impossible_under_concurrency():
    """RES-6 — enforced by the database, not the application."""
    with ThreadPoolExecutor(10) as ex:
        results = list(ex.map(lambda _: try_book(table, slot), range(10)))
    assert sum(r.ok for r in results) == 1
```

---

## 8. Factories

```python
class MenuItemFactory(DjangoModelFactory):
    class Meta: model = MenuItem
    name = Faker("word")
    slug = LazyAttribute(lambda o: slugify(o.name))
    base_price = 1_000_000                 # ₦10,000 — always explicit kobo
    needs_repricing = False                # tests use confirmed prices
    tax_class = "standard"
    is_available_now = True
```

Never `Faker("pydecimal")` for money. Every fixture price is an explicit, readable kobo integer.

---

## 9. CI pipeline

```yaml
- ruff check . && ruff format --check .
- mypy apps/common apps/carts/services apps/payments/services apps/orders/services
- pytest --cov=apps --cov-fail-under=85
- pytest apps/common/tests/test_money.py --cov=apps.common.money --cov-fail-under=100
- pytest apps/carts apps/promotions apps/orders apps/payments apps/loyalty apps/academy \
         --cov=apps.carts.services --cov=apps.promotions.services \
         --cov=apps.orders.services --cov=apps.payments.services \
         --cov=apps.payments.tasks --cov=apps.payments.providers \
         --cov=apps.loyalty.services --cov=apps.academy.services \
         --cov-fail-under=100                              # money path: pricing, rewards, enrolments, providers
- python manage.py check --deploy --fail-level WARNING
- python manage.py makemigrations --check --dry-run     # no un-committed migrations
- gitleaks detect --no-git
- ./scripts/check-no-card-fields.sh                     # PCI gate
- ./scripts/check-no-price-arithmetic.sh                # components render Money.display
- ./scripts/check-no-alert.sh                           # PRD §9 (11): no native dialogs
- pip-audit
```

---

## 10. Load testing

Before Gate 1, with Locust:

| Scenario | Target |
|---|---|
| 200 concurrent order-status polls | p95 < 100 ms |
| 50 concurrent order placements | zero duplicates, zero lost orders |
| Menu browse, 500 rps | p95 < 200 ms (cached) |
| KDS poll, 10 clients @ 10s | no lock contention |
