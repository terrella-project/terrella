#!/usr/bin/env bash
# Compare available provider models against what is configured in litellm/config.yaml.
# Reports: configured models, new models not yet in config, stale models no longer available.
#
# Usage: ./scripts/list-models.sh [anthropic|gemini|ollama|all]
#   Default: all
#
# Note: ollama does NOT auto-update models. Use scripts/update-ollama-models.sh to pull latest.

set -euo pipefail

cd "$(dirname "$0")/.."

CONFIG="observability/litellm/config.yaml"

if [[ ! -f .env ]]; then
    echo "ERROR: .env not found. Run scripts/generate-env.sh first." >&2
    exit 1
fi

# shellcheck disable=SC1091
source .env

target="${1:-all}"

# Extract raw model IDs from litellm_params in config.yaml for a given provider prefix.
configured_ids() {
    local prefix="$1"
    grep -E "^\s+model: ${prefix}/" "$CONFIG" \
        | sed -E "s|.*model: ${prefix}/||" \
        | sort
}

# Print diff between configured and available sets.
diff_report() {
    local configured="$1"
    local available="$2"

    local new stale
    new=$(comm -13 <(echo "$configured" | sort -u) <(echo "$available" | sort -u))
    stale=$(comm -23 <(echo "$configured" | sort -u) <(echo "$available" | sort -u))

    if [[ -n "$new" ]]; then
        echo "  [NEW — not in config]:"
        echo "$new" | sed 's/^/    + /'
    fi
    if [[ -n "$stale" ]]; then
        echo "  [STALE — in config but no longer available]:"
        echo "$stale" | sed 's/^/    - /'
    fi
    if [[ -z "$new" && -z "$stale" ]]; then
        echo "  config is up to date."
    fi
}

# ── Anthropic ──────────────────────────────────────────────────────────────
if [[ "$target" == "anthropic" || "$target" == "all" ]]; then
    echo "=== Anthropic ==="
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        echo "  ANTHROPIC_API_KEY not set — skipping."
    else
        available=$(curl -s https://api.anthropic.com/v1/models \
            -H "x-api-key: $ANTHROPIC_API_KEY" \
            -H "anthropic-version: 2023-06-01" \
            | python3 -c "
import sys, json
for m in json.load(sys.stdin).get('data', []):
    print(m['id'])
" | sort)

        configured=$(configured_ids "anthropic")

        echo "  Available from API:"
        echo "$available" | sed 's/^/    /'
        echo
        diff_report "$configured" "$available"
    fi
    echo
fi

# ── Google Gemini ──────────────────────────────────────────────────────────
if [[ "$target" == "gemini" || "$target" == "all" ]]; then
    echo "=== Gemini ==="
    if [[ -z "${GEMINI_API_KEY:-}" ]]; then
        echo "  GEMINI_API_KEY not set — skipping."
    else
        available=$(curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" \
            | python3 -c "
import sys, json
for m in json.load(sys.stdin).get('models', []):
    name = m.get('name','').replace('models/','')
    if 'gemini' in name.lower():
        print(name)
" | sort)

        configured=$(configured_ids "gemini")

        echo "  Available from API:"
        echo "$available" | sed 's/^/    /'
        echo
        diff_report "$configured" "$available"
    fi
    echo
fi

# ── ollama (local) ─────────────────────────────────────────────────────────
if [[ "$target" == "ollama" || "$target" == "all" ]]; then
    echo "=== ollama (local) ==="
    if ! curl -sf --max-time 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ollama not reachable on localhost:11434 — is it running?"
    else
        available=$(curl -s http://localhost:11434/api/tags \
            | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    size_gb = m.get('size', 0) / 1e9
    print(f\"{m['name']}  ({size_gb:.1f} GB)\")
" | sort)

        configured=$(grep -E "^\s+model: ollama/" "$CONFIG" \
            | sed 's|.*model: ollama/||' \
            | sort)

        available_names=$(echo "$available" | awk '{print $1}' | sort)

        echo "  Installed:"
        echo "$available" | sed 's/^/    /'
        echo
        diff_report "$configured" "$available_names"
    fi
    echo
fi

echo "After updating config.yaml: docker compose restart litellm"
