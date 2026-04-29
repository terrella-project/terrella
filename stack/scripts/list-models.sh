#!/usr/bin/env bash
# Compare available provider models against what is configured in litellm/config.yaml.
# Reports: configured models, new models not yet in config, stale models no longer available.
#
# Usage: ./scripts/list-models.sh [anthropic|gemini|openai|ollama|all]
#   Default: all
#
# Note: ollama does NOT auto-update models. Use scripts/update-ollama-models.sh to pull latest.

set -euo pipefail

cd "$(dirname "$0")/.."

CONFIG="observability/litellm/config.yaml"
HELPER="scripts/provider-models.py"

if [[ ! -f .env ]]; then
    echo "ERROR: .env not found. Run scripts/generate-env.sh first." >&2
    exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

target="${1:-all}"

# Extract raw model IDs from litellm_params in config.yaml for a given provider prefix.
configured_ids() {
    local prefix="$1"
    grep -E "^[[:space:]]+model: ${prefix}/" "$CONFIG" \
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

print_list() {
    local heading="$1"
    local values="$2"

    echo "$heading"
    if [[ -n "$values" ]]; then
        echo "$values" | sed 's/^/    /'
    else
        echo "    (none)"
    fi
}

# ── Anthropic ──────────────────────────────────────────────────────────────
if [[ "$target" == "anthropic" || "$target" == "all" ]]; then
    echo "=== Anthropic ==="
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        echo "  ANTHROPIC_API_KEY not set — skipping."
    else
        configured=$(configured_ids "anthropic")
        available=$("$HELPER" anthropic)

        print_list "  Configured in config.yaml:" "$configured"
        echo
        print_list "  Available from API:" "$available"
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
        configured=$(configured_ids "gemini")
        available=$("$HELPER" gemini)

        print_list "  Configured in config.yaml:" "$configured"
        echo
        print_list "  Available from API:" "$available"
        echo
        diff_report "$configured" "$available"
    fi
    echo
fi

# ── OpenAI ─────────────────────────────────────────────────────────────────
if [[ "$target" == "openai" || "$target" == "all" ]]; then
    echo "=== OpenAI ==="
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        echo "  OPENAI_API_KEY not set — skipping."
    else
        configured=$(configured_ids "openai")
        available=$("$HELPER" openai)

        print_list "  Configured in config.yaml:" "$configured"
        echo
        print_list "  Available from API (stable core models):" "$available"
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
        configured=$(grep -E "^[[:space:]]+model: ollama/" "$CONFIG" \
            | sed 's|.*model: ollama/||' \
            | sort)
        available=$("$HELPER" ollama)

        print_list "  Configured in config.yaml:" "$configured"
        echo
        print_list "  Installed locally:" "$available"
        echo
        diff_report "$configured" "$available"
    fi
    echo
fi

echo "After updating config.yaml: docker compose restart litellm"
