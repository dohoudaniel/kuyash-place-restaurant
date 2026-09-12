#!/usr/bin/env bash
#
# PCI-DSS structural gate — FRONTEND half (docs/PAYMENTS.md §1.1).
#
# Raw cardholder data must never reach our infrastructure. Payment goes through
# Paystack/Flutterwave hosted checkout.
#
# Scope: this script scans `frontend/` only.
#
# The backend is covered by apps/payments/tests/test_no_card_data.py, which
# walks the AST instead of the text. That distinction matters: a text scan
# cannot tell a real field from a docstring saying "there is no CVV field here",
# or from a test whose whole purpose is to send card fields and assert they are
# discarded. An earlier version of this script flagged all three and the fix
# would have been an ever-growing exclusion list. AST analysis has no such
# problem, so the backend uses it and this script stays where no AST tooling is
# readily at hand.
#
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 2

PATTERN='cardNumber|cardCvv|cardExpiry|card_number|card_cvv|card_expiry|\bcvv\b|\bCVV\b'
# Display-only values a payment provider legitimately returns.
ALLOWED_TOKENS='card_last4|card_brand|card_exp_month|card_exp_year|cardholder'

# Pre-existing frontend debt, scheduled for DELETION in Phase 1
# (docs/FRONTEND_INTEGRATION.md §2). This list may only shrink.
KNOWN_FRONTEND_DEBT=(
  "frontend/components/features/checkout/PaymentStep.tsx"
  "frontend/components/features/checkout/PaymentStepCompact.tsx"
  "frontend/components/features/checkout/ReviewStep.tsx"
  "frontend/components/features/checkout/ReviewStepCompact.tsx"
  "frontend/components/features/account/PaymentMethodsSection.tsx"
)

hits="$(grep -rnIE "$PATTERN" frontend \
  --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' \
  --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=docs 2>/dev/null \
  | grep -vE "$ALLOWED_TOKENS" || true)"

status=0
if [[ -n "$hits" ]]; then
  unexpected=""
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    file="${line%%:*}"
    known=0
    for allowed in "${KNOWN_FRONTEND_DEBT[@]}"; do
      [[ "$file" == "$allowed" ]] && known=1 && break
    done
    [[ $known -eq 0 ]] && unexpected+="$line"$'\n'
  done <<< "$hits"

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
    echo "   Remove them from KNOWN_FRONTEND_DEBT here once deleted."
  fi
fi

if [[ $status -eq 0 ]]; then
  echo "✅ Frontend: no card fields outside the documented Phase 1 deletion list."
  echo "   Backend is covered by apps/payments/tests/test_no_card_data.py (AST)."
fi
exit $status
