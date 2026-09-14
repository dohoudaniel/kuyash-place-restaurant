#!/usr/bin/env bash
#
# Money gate — FRONTEND (docs/FRONTEND_INTEGRATION.md §6).
#
# The server prices everything. Components render `Money.display` and never do
# arithmetic on `Money.amount` or format currency themselves: two places that
# compute a total will eventually disagree, and the customer is charged the
# server's figure regardless of what the page showed.
#
# This is a text scan, so it looks for the shapes money arithmetic actually
# takes rather than every `*` in the codebase:
#   - arithmetic on a `.amount` field           (cart.totals.tip.amount * 2)
#   - currency formatting in the browser         (Intl.NumberFormat, style: "currency")
#   - naira strings built by hand                (`₦${price}`, "₦" + total)
#
# A deliberate exception belongs in ALLOWED_LINES with a reason, not in a
# broader pattern.
#
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 2

PATTERN='\.amount[[:space:]]*[-+*/%]|[-+*/%][[:space:]]*[A-Za-z_.?]*\.amount\b|Intl\.NumberFormat|style:[[:space:]]*["'"'"']currency|₦\$\{|["'"'"']₦["'"'"'][[:space:]]*\+'

# file:line-content fragments that are allowed. Keep empty unless justified.
ALLOWED_LINES=()

hits="$(grep -rnIE "$PATTERN" frontend/app frontend/components frontend/lib \
  --include='*.ts' --include='*.tsx' \
  --exclude='schema.d.ts' 2>/dev/null || true)"

unexpected=""
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  allowed=0
  for fragment in "${ALLOWED_LINES[@]}"; do
    [[ "$line" == *"$fragment"* ]] && allowed=1 && break
  done
  [[ $allowed -eq 0 ]] && unexpected+="$line"$'\n'
done <<< "$hits"

if [[ -n "$unexpected" ]]; then
  echo "❌ Money arithmetic or currency formatting found in the frontend:"
  echo "$unexpected"
  echo "   Render Money.display from the API instead. See backend/docs/FRONTEND_INTEGRATION.md §6."
  exit 1
fi

echo "✅ Frontend: no money arithmetic or client-side currency formatting."
