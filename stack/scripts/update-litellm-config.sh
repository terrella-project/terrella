#!/usr/bin/env bash
# Refresh the managed provider catalogs in observability/litellm/config.yaml.
#
# Usage:
#   ./scripts/update-litellm-config.sh
#   ./scripts/update-litellm-config.sh openai
#   ./scripts/update-litellm-config.sh --dry-run

set -euo pipefail

cd "$(dirname "$0")/.."

CONFIG="observability/litellm/config.yaml"
HELPER="scripts/provider-models.py"
DRY_RUN=false
target="all"

usage() {
    sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        anthropic|gemini|openai|ollama|all)
            target="$1"
            shift
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown arg: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ ! -f .env ]]; then
    echo "ERROR: .env not found. Run scripts/generate-env.sh first." >&2
    exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

if [[ ! -f "$CONFIG" ]]; then
    echo "ERROR: $CONFIG not found." >&2
    exit 1
fi

providers=(anthropic gemini openai ollama)
if [[ "$target" != "all" ]]; then
    providers=("$target")
fi

print_model_block() {
    local provider="$1"
    local models="$2"

    if [[ "$provider" == "anthropic" ]]; then
        echo "  # Available raw model IDs (managed by update-litellm-config.sh)."
        echo "  # >>> anthropic catalog (managed by update-litellm-config.sh) >>>"
        while IFS= read -r model; do
            [[ -n "$model" ]] || continue
            printf '  - model_name: %s\n' "$model"
            printf '    litellm_params:\n'
            printf '      model: anthropic/%s\n' "$model"
            printf '      api_key: os.environ/ANTHROPIC_API_KEY\n'
        done <<< "$models"
        echo "  # <<< anthropic catalog <<<"
        return
    fi

    if [[ "$provider" == "gemini" ]]; then
        echo "  # Available raw model IDs (managed by update-litellm-config.sh)."
        echo "  # >>> gemini catalog (managed by update-litellm-config.sh) >>>"
        while IFS= read -r model; do
            [[ -n "$model" ]] || continue
            printf '  - model_name: %s\n' "$model"
            printf '    litellm_params:\n'
            printf '      model: gemini/%s\n' "$model"
            printf '      api_key: os.environ/GEMINI_API_KEY\n'
        done <<< "$models"
        echo "  # <<< gemini catalog <<<"
        return
    fi

    if [[ "$provider" == "openai" ]]; then
        echo "  # Stable core model IDs (managed by update-litellm-config.sh)."
        echo "  # >>> openai catalog (managed by update-litellm-config.sh) >>>"
        while IFS= read -r model; do
            [[ -n "$model" ]] || continue
            printf '  - model_name: %s\n' "$model"
            printf '    litellm_params:\n'
            printf '      model: openai/%s\n' "$model"
            printf '      api_key: os.environ/OPENAI_API_KEY\n'
        done <<< "$models"
        echo "  # <<< openai catalog <<<"
        return
    fi

    echo "  # Installed raw model IDs (managed by update-litellm-config.sh)."
    echo "  # >>> ollama catalog (managed by update-litellm-config.sh) >>>"
    while IFS= read -r model; do
        local model_name
        [[ -n "$model" ]] || continue
        model_name=${model//:/-}
        printf '  - model_name: ollama/%s\n' "$model_name"
        printf '    litellm_params:\n'
        printf '      model: ollama/%s\n' "$model"
        printf '      api_base: http://127.0.0.1:11434\n'
    done <<< "$models"
    echo "  # <<< ollama catalog <<<"
}

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

generated_any=false
for provider in "${providers[@]}"; do
    echo "Fetching $provider models..." >&2
    models="$("$HELPER" "$provider")"
    print_model_block "$provider" "$models" > "$tmpdir/$provider.block"
    generated_any=true
done

if ! $generated_any; then
    echo "ERROR: nothing to update." >&2
    exit 1
fi

provider_csv=$(IFS=,; echo "${providers[*]}")

updated=$(python3 - "$CONFIG" "$tmpdir" "$provider_csv" <<'PY'
from __future__ import annotations

import pathlib
import re
import sys

config_path = pathlib.Path(sys.argv[1])
block_dir = pathlib.Path(sys.argv[2])
providers = [item for item in sys.argv[3].split(",") if item]

text = config_path.read_text()

for provider in providers:
    begin = f"  # >>> {provider} catalog (managed by update-litellm-config.sh) >>>"
    end = f"  # <<< {provider} catalog <<<"
    block_path = block_dir / f"{provider}.block"
    block = block_path.read_text().rstrip("\n")

    pattern = re.compile(
        rf"{re.escape(begin)}.*?{re.escape(end)}",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"ERROR: markers missing for provider '{provider}' in {config_path}")
    text = pattern.sub(block, text, count=1)

print(text, end="")
PY
)

if $DRY_RUN; then
    echo "----- updated config (dry run) -----"
    echo "$updated"
    exit 0
fi

printf '%s' "$updated" > "$CONFIG"
echo "Wrote $CONFIG"
echo "Restart LiteLLM: docker compose restart litellm"
