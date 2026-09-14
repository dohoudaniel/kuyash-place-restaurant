#!/usr/bin/env bash
#
# PRD §9 criterion 11 — no alert() in any submission path.
#
# The frontend used to "submit" forms with alert("Reservation submitted!") and
# nothing was sent anywhere. Every form now calls the API and shows the result in
# the page. This gate stops a browser dialog coming back as a stand-in for a real
# request or a real error message.
#
# Scans frontend/app, components and lib. Lines that are comments (starting with
# //, /* or *) are skipped: several files explain in prose what the old alert()
# used to do.
#
set -uo pipefail

cd "$(dirname "$0")/../../frontend" || exit 2

# A bare alert( call, or any native dialog reached through window. Bare confirm(
# and prompt( are not flagged: local functions use those names (the reservations
# page has `const confirm = async () => …`).
PATTERN='(^|[^A-Za-z0-9_.$])alert[[:space:]]*\(|window\.(alert|confirm|prompt)[[:space:]]*\('

# Must stay empty. A native dialog is not a submission result or an error message.
ALLOWED_LINES=()

hits="$(grep -rnIE "$PATTERN" app components lib \
  --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' 2>/dev/null \
  | grep -vE '^[^:]+:[0-9]+:[[:space:]]*(//|/\*|\*)' || true)"

unexpected=""
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  known=0
  for allowed in "${ALLOWED_LINES[@]}"; do
    [[ "$line" == *"$allowed"* ]] && known=1 && break
  done
  [[ $known -eq 0 ]] && unexpected+="$line"$'\n'
done <<< "$hits"

if [[ -n "$unexpected" ]]; then
  echo "❌ Native browser dialogs found in the frontend:"
  echo "$unexpected"
  echo "   Show the API's result or error in the page instead. See backend/PRD.md §9 (11)."
  exit 1
fi

echo "✅ Frontend: no alert() and no window.confirm()/prompt() calls."
exit 0
