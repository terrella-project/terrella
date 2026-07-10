#!/usr/bin/env bash
# terrella quadlet stack — installer.
#
# Idempotent. Performs the render + link steps the M1 CLI will absorb
# (ADR-0006): rendered artifacts live under ~/.config/terrella/, unit files are
# symlinked into the systemd/quadlet search paths, secrets are split from
# stack/.env into per-service env files so no container sees another's keys.
#
#   install.sh          render configs, split env, link units, daemon-reload
#   install.sh --check  show what would change, touch nothing

set -euo pipefail

QUADLET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK_DIR="$(dirname "$QUADLET_DIR")"
CFG="$HOME/.config/terrella"
UNIT_DST="$HOME/.config/containers/systemd"
TARGET_DST="$HOME/.config/systemd/user"
CHECK_ONLY="${1:-}"

run() { if [[ $CHECK_ONLY == --check ]]; then echo "  would: $*"; else "$@"; fi; }

echo "▶ rendered configs → $CFG"
if [[ $CHECK_ONLY != --check ]]; then
    mkdir -p "$CFG"/{litellm,prometheus,exporters,env.d} && chmod 700 "$CFG/env.d"

    # LiteLLM config: single source of truth is the legacy tree; the only
    # transform is host networking → host-gateway for ollama (spike #6).
    sed 's|http://127.0.0.1:11434|http://host.containers.internal:11434|g' \
        "$STACK_DIR/observability/litellm/config.yaml" > "$CFG/litellm/config.yaml"

    install -m 644 "$QUADLET_DIR/config/prometheus.yml" "$CFG/prometheus/prometheus.yml"

    # Grafana provisioning tree: dashboards come from the legacy tree unchanged,
    # datasources are the quadlet version (container DNS names).
    rm -rf "$CFG/grafana/provisioning"
    mkdir -p "$CFG/grafana"
    cp -r "$STACK_DIR/observability/grafana/provisioning" "$CFG/grafana/provisioning"
    install -m 644 "$QUADLET_DIR/config/grafana-datasources.yml" \
        "$CFG/grafana/provisioning/datasources/datasources.yml"

    install -m 644 "$STACK_DIR/observability/litellm/litellm_exporter.py" "$CFG/exporters/"
    install -m 644 "$STACK_DIR/observability/ollama/ollama_exporter.py" "$CFG/exporters/"
fi

echo "▶ per-service env files → $CFG/env.d"
ENV_SRC="$STACK_DIR/.env"
if [[ ! -f $ENV_SRC ]]; then
    echo "  ✖ $ENV_SRC missing — create it (scripts/generate-env.sh, or restore env.backup)" >&2
    exit 1
fi
if [[ $CHECK_ONLY != --check ]]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_SRC"; set +a
    : "${OPENWEBUI_DB:=openwebui}"
    umask 177
    cat > "$CFG/env.d/postgres.env" <<EOF
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB
EOF
    cat > "$CFG/env.d/litellm.env" <<EOF
DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@terrella-postgres:5432/$POSTGRES_DB
LITELLM_MASTER_KEY=$LITELLM_MASTER_KEY
LITELLM_SALT_KEY=$LITELLM_SALT_KEY
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
GEMINI_API_KEY=${GEMINI_API_KEY:-}
OPENAI_API_KEY=${OPENAI_API_KEY:-}
EOF
    # github-mcp ≥ v1.0: streamable HTTP at /mcp with per-request bearer auth
    # (SSE and env-only auth are gone), so the connection JSON carries the PAT.
    cat > "$CFG/env.d/openwebui.env" <<EOF
DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@terrella-postgres:5432/$OPENWEBUI_DB
TOOL_SERVER_CONNECTIONS=[{"type":"mcp","url":"http://terrella-github-mcp:8765/mcp","auth_type":"bearer","key":"${GITHUB_PAT:-}","name":"GitHub","description":"GitHub MCP - repos, issues, PRs, code search"}]
EOF
    cat > "$CFG/env.d/grafana.env" <<EOF
GF_SECURITY_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB
EOF
    cat > "$CFG/env.d/github-mcp.env" <<EOF
GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PAT:-}
EOF
    cat > "$CFG/env.d/litellm-exporter.env" <<EOF
LITELLM_EXPORTER_API_KEY=${LITELLM_EXPORTER_API_KEY:-}
EOF
    umask 022
fi

# Units are COPIED, not symlinked: the deployed stack must not break when the
# repo checkout switches to a branch without stack/quadlet/ (learned the hard
# way — a broken symlink at daemon-reload deletes the generated service).
# Copying is also exactly what the M1 renderer will do.
echo "▶ quadlet units → $UNIT_DST, targets → $TARGET_DST"
run mkdir -p "$UNIT_DST" "$TARGET_DST"
for f in "$QUADLET_DIR"/*.container "$QUADLET_DIR"/*.network "$QUADLET_DIR"/*.volume; do
    run install -m 644 "$f" "$UNIT_DST/$(basename "$f")"
done
for f in "$QUADLET_DIR"/*.target "$QUADLET_DIR"/*.service; do
    run install -m 644 "$f" "$TARGET_DST/$(basename "$f")"
done

echo "▶ pre-pull pinned images (units assume images exist; no AutoUpdate — D5)"
grep -h '^Image=' "$QUADLET_DIR"/*.container | cut -d= -f2 | sort -u | while read -r img; do
    if podman image exists "$img"; then
        echo "  ✔ $img"
    else
        run podman pull "$img"
    fi
done

# Quadlet-generated units get their [Install] wiring from the generator, but
# plain units (targets, ollama.service) need an explicit enable to create the
# .wants links (boot start via default.target + target membership).
echo "▶ systemd reload + enable boot start"
run systemctl --user daemon-reload
run systemctl --user enable terrella.target terrella-inference.target ollama.service

echo
echo "Done. Next: systemctl --user start terrella.target"
echo "  (first start on a new machine: restore data first — docs/runbooks/fedora-migration.md)"
