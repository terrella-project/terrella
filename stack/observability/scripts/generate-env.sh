#!/usr/bin/env bash
# Generate the .env in this directory with strong random secrets.
# Idempotent: refuses to overwrite an existing .env unless --force is passed.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env && "${1:-}" != "--force" ]]; then
    echo "ERROR: .env already exists. Pass --force to overwrite." >&2
    exit 1
fi

rand() {
    # 32 url-safe bytes
    openssl rand -base64 32 | tr -d '\n=' | tr '/+' '_-'
}

cat > .env <<EOF
# Generated $(date -Iseconds) by scripts/generate-env.sh — do not commit.
POSTGRES_USER=litellm
POSTGRES_PASSWORD=$(rand)
POSTGRES_DB=litellm
LITELLM_MASTER_KEY=sk-master-$(rand)
LITELLM_SALT_KEY=$(rand)
GRAFANA_ADMIN_PASSWORD=$(rand)
EOF
chmod 600 .env

# Pre-create bind-mount directories so Docker doesn't create them as root,
# which would prevent Grafana (uid 472) from writing its data directory.
mkdir -p data/postgres data/prometheus data/grafana
chmod 750 data/postgres data/prometheus
chmod 777 data/grafana   # Grafana container uid 472 needs write access

echo "Wrote $(pwd)/.env (mode 600)."
echo "Created data/ subdirectories."
echo "Backend provider keys (ANTHROPIC_API_KEY etc.) must be exported in the calling shell."
echo "On earth, those come from ~/.config/trackpro/secrets via ~/.bashrc."
