#!/usr/bin/env bash
#
# PCI-DSS structural gate (docs/PAYMENTS.md §1.1).
#
# Raw cardholder data must never reach our infrastructure. Payment goes through
# Paystack/Flutterwave hosted checkout, so no card number, expiry or CVV should
# appear in application code anywhere.
#
# backend/  : any hit is a hard failure. There is no legitimate reason for a
#             card field to exist server-side, ever.
# frontend/ : hits are failures too, EXCEPT for the known pre-existing files
#             listed in KNOWN_FRONTEND_DEBT below. Those are scheduled for
#             deletion in Phase 1 (docs/FRONTEND_INTEGRATION.md §2). The
#             allowlist can only shrink — a hit in any other file fails now.
#
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 2

PATTERN='cardNumber|cardCvv|cardExpiry|card_number|card_cvv|card_expiry|\bcvv\b|\bCVV\b'
# Display-only fields a payment provider legitimately returns to us.
ALLOWED_TOKENS='card_last4|card_brand|card_exp_month|card_exp_year|cardholder'

# Pre-existing frontend debt, scheduled for deletion in Phase 1.
# NOTE: the Review steps were NOT in the original audit — this gate found them.
# The PAN propagates from the payment step into the review step, which renders
# `paymentData.cardNumber.slice(-4)`. All of these are deletions, not rewrites.
KNOWN_FRONTEND_DEBT=(
  "frontend/components/features/checkout/PaymentStep.tsx"
  "frontend/components/features/checkout/PaymentStepCompact.tsx"
  "frontend/components/features/checkout/ReviewStep.tsx"
  "frontend/components/features/checkout/ReviewStepCompact.tsx"
  "frontend/components/features/account/PaymentMethodsSection.tsx"
)

# The Sentry scrubber names these keys in order to REDACT them. Listing a key on
# a denylist is the opposite of handling card data, so these files are exempt.
EXCLUDED_PATHS=(
  "backend/apps/common/observability.py"
  "backend/apps/common/tests/test_observability.py"
)

scan() {
  local dir="$1"
  local hits
  hits="$(grep -rnIE "$PATTERN" "$dir" \
    --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.py' \
    --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.next \
    --exclude-dir=migrations --exclude-dir=docs --exclude-dir=.git 2>/dev/null \
    | grep -vE "$ALLOWED_TOKENS" || true)"

  for excluded in "${EXCLUDED_PATHS[@]}"; do
    hits="$(printf '%s\n' "$hits" | grep -v "^${excluded}:" || true)"
  done
  printf '%s' "$hits"
}

status=0

backend_hits="$(scan backend)"
if [[ -n "$backend_hits" ]]; then
  echo "❌ Card data fields found in backend/ — this must never exist server-side:"
  echo "$backend_hits"
  status=1
fi

frontend_hits="$(scan frontend)"
if [[ -n "$frontend_hits" ]]; then
  unexpected=""
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    file="${line%%:*}"
    known=0
    for allowed in "${KNOWN_FRONTEND_DEBT[@]}"; do
      [[ "$file" == "$allowed" ]] && known=1 && break
    done
    [[ $known -eq 0 ]] && unexpected+="$line"$'\n'
  done <<< "$frontend_hits"

  if [[ -n "$unexpected" ]]; then
    echo "❌ Card data fields found in unexpected frontend files:"
    echo "$unexpected"
    echo "   Payments must use hosted provider checkout. See backend/docs/PAYMENTS.md §1."
    status=1
  else
    echo "⚠️  Known pre-existing card fields remain in:"
    for allowed in "${KNOWN_FRONTEND_DEBT[@]}"; do
      [[ -f "$allowed" ]] && echo "     $allowed"
    done
    echo "   These are scheduled for DELETION in Phase 1 (not connection)."
    echo "   Remove them from KNOWN_FRONTEND_DEBT in this script once deleted."
  fi
fi

if [[ $status -eq 0 ]]; then
  echo "✅ No card data fields outside the documented Phase 1 deletion list."
fi
exit $status
