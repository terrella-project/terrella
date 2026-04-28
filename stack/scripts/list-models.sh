#!/usr/bin/env bash
# List available models from each configured provider.
# Run this to check which model IDs are current before updating config.yaml.
#
# Usage: ./scripts/list-models.sh [anthropic|gemini|ollama|all]
#   Default: all
#
# Note: ollama does NOT auto-update models. Re-run `ollama pull <model>` to update.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
    echo "ERROR: .env not found. Run scripts/generate-env.sh first." >&2
    exit 1
fi

# shellcheck disable=SC1091
source .env

target="${1:-all}"

# ── Anthropic ──────────────────────────────────────────────────────────────
if [[ "$target" == "anthropic" || "$target" == "all" ]]; then
    echo "=== Anthropic models ==="
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        echo "  ANTHROPIC_API_KEY not set — skipping."
    else
        curl -s https://api.anthropic.com/v1/models \
            -H "x-api-key: $ANTHROPIC_API_KEY" \
            -H "anthropic-version: 2023-06-01" \
            | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('data', []):
    print(f\"  {m['id']}\")
"
    fi
    echo
fi

# ── Google Gemini ──────────────────────────────────────────────────────────
if [[ "$target" == "gemini" || "$target" == "all" ]]; then
    echo "=== Gemini models ==="
    if [[ -z "${GEMINI_API_KEY:-}" ]]; then
        echo "  GEMINI_API_KEY not set — skipping."
    else
        curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" \
            | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    name = m.get('name','').replace('models/','')
    if 'gemini' in name.lower():
        print(f\"  {name}\")
"
    fi
    echo
fi

# ── ollama (local) ─────────────────────────────────────────────────────────
if [[ "$target" == "ollama" || "$target" == "all" ]]; then
    echo "=== ollama models (locally installed) ==="
    if curl -sf --max-time 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
        curl -s http://localhost:11434/api/tags \
            | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    size_gb = m.get('size', 0) / 1e9
    print(f\"  {m['name']:<45} {size_gb:.1f} GB\")
"
    else
        echo "  ollama not reachable on localhost:11434 — is it running?"
    fi
    echo
fi

echo "Update stack/observability/litellm/config.yaml with any new IDs, then:"
echo "  docker compose restart litellm"
echo
echo "To update an ollama model to the latest version of its tag:"
echo "  ollama pull <model>:<tag>"
