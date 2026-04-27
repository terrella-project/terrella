#!/usr/bin/env bash
# One-time: create the manual subscription tracking table in the LiteLLM Postgres.
# Re-running is safe (CREATE TABLE IF NOT EXISTS).

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
    echo "ERROR: .env not found. Run scripts/generate-env.sh first." >&2
    exit 1
fi
# shellcheck disable=SC1091
set -a; source .env; set +a

docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < sql/monthly_costs.sql

echo "monthly_costs table is ready."
