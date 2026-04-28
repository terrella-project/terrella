#!/usr/bin/env bash
# Pull the latest version of every installed ollama model.
# Also pulls any models in provision/models.list that are not yet installed.
#
# Usage: ./scripts/update-ollama-models.sh [--installed-only]
#   --installed-only   skip models.list; only re-pull already-installed models

set -euo pipefail

cd "$(dirname "$0")/../.."   # repo root

MODELS_LIST="provision/models.list"
installed_only=false
[[ "${1:-}" == "--installed-only" ]] && installed_only=true

if ! curl -sf --max-time 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: ollama not reachable on localhost:11434 — is it running?" >&2
    exit 1
fi

echo "=== Updating installed ollama models ==="
installed=$(curl -s http://localhost:11434/api/tags \
    | python3 -c "
import sys, json
for m in json.load(sys.stdin).get('models', []):
    print(m['name'])
")

if [[ -z "$installed" ]]; then
    echo "  No models currently installed."
else
    while IFS= read -r model; do
        echo
        echo "Pulling $model..."
        ollama pull "$model"
    done <<< "$installed"
fi

if [[ "$installed_only" == false && -f "$MODELS_LIST" ]]; then
    echo
    echo "=== Checking provision/models.list for missing models ==="
    while IFS= read -r line; do
        # strip comments and blank lines
        model=$(echo "$line" | sed 's/#.*//' | xargs)
        [[ -z "$model" ]] && continue

        if echo "$installed" | grep -qF "$model"; then
            echo "  $model — already installed (updated above)"
        else
            echo
            echo "  $model not installed — pulling..."
            ollama pull "$model"
        fi
    done < "$MODELS_LIST"
fi

echo
echo "Done. Run ./stack/scripts/list-models.sh ollama to verify."
