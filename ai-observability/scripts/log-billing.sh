#!/usr/bin/env bash
# Interactively insert (or upsert) a subscription cost row.
# Use after each Copilot / Claude Code billing cycle.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
    echo "ERROR: .env not found. Run scripts/generate-env.sh first." >&2
    exit 1
fi
# shellcheck disable=SC1091
set -a; source .env; set +a

read -rp "Month (YYYY-MM): " month
read -rp "Vendor (copilot|claude-code|anthropic|gemini|other): " vendor
read -rp "Amount USD: " amount
read -rp "Notes (optional): " notes

if [[ ! "$month" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
    echo "ERROR: month must be YYYY-MM (e.g. 2026-04)." >&2
    exit 1
fi
if [[ ! "$amount" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "ERROR: amount must be a number." >&2
    exit 1
fi

# psql via docker compose. Use parameters to avoid quoting issues on notes.
docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
    -v month="${month}-01" -v vendor="$vendor" -v amount="$amount" -v notes="$notes" <<'SQL'
INSERT INTO monthly_costs (month, vendor, amount_usd, notes)
VALUES (:'month'::date, :'vendor', :'amount'::numeric, NULLIF(:'notes',''))
ON CONFLICT (month, vendor) DO UPDATE
SET amount_usd = EXCLUDED.amount_usd,
    notes      = EXCLUDED.notes,
    created_at = now();
SQL

echo "Recorded $vendor $amount USD for $month."
