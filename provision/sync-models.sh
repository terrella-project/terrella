#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Ollama model manager for WSL / Linux
#
# Reads model names from models.list (or $MODELS_FILE) and
# pulls each one. Safe to re-run — ollama pull is a no-op
# when a model is already up to date.
#
# Usage:
#   ./sync-models.sh
#   MODELS_FILE=/path/to/other.list ./sync-models.sh
#
# It then reads agent-models.list (or $AGENT_MODELS_FILE): each line
# names a model and a context size, and gets a "<model>-<N>k" variant
# with that context, for agent harnesses (see that file).
#
# To add or remove models, edit models.list.
# To remove an already-pulled model from Ollama, run:
#   ollama rm <model-name>
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_FILE="${MODELS_FILE:-${SCRIPT_DIR}/models.list}"
AGENT_MODELS_FILE="${AGENT_MODELS_FILE:-${SCRIPT_DIR}/agent-models.list}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Error: ollama is not installed or not in PATH."
  echo "Run provision.sh first, then re-run this script."
  exit 1
fi

if [[ ! -f "$MODELS_FILE" ]]; then
  echo "Error: model list not found: ${MODELS_FILE}"
  echo "Expected: ${MODELS_FILE}"
  exit 1
fi

pull_model() {
  local model="$1"
  echo
  echo "============================================================"
  echo "Pulling model: $model"
  echo "============================================================"
  ollama pull "$model"
}

echo "Starting Ollama model installation..."
echo "Model list: ${MODELS_FILE}"
echo

while IFS= read -r model; do
  [[ -z "$model" ]] && continue
  pull_model "$model"
done < <(sed -E 's/#.*$//; s/[[:space:]]+$//; /^[[:space:]]*$/d' "$MODELS_FILE" \
          | awk '{print $1}')

# An agent variant is the same model with a larger context window. `ollama create`
# reuses the weights already on disk, and re-creating an unchanged variant is a no-op.
create_agent_variant() {
  local model="$1" context="$2"
  if ! [[ "$context" =~ ^[0-9]+$ ]] || (( context < 1024 )); then
    echo "Error: ${AGENT_MODELS_FILE}: context for ${model} must be a number of tokens, not '${context}'." >&2
    exit 1
  fi
  local variant="${model}-$(( context / 1024 ))k" modelfile
  pull_model "$model"
  modelfile="$(mktemp)"
  printf 'FROM %s\nPARAMETER num_ctx %s\n' "$model" "$context" > "$modelfile"
  echo "Creating agent variant: $variant (context $context)"
  ollama create "$variant" -f "$modelfile"
  rm -f "$modelfile"
}

if [[ -f "$AGENT_MODELS_FILE" ]]; then
  while read -r model context _; do
    [[ -z "$model" ]] && continue
    create_agent_variant "$model" "${context:-}"
  done < <(sed -E 's/#.*$//; s/[[:space:]]+$//; /^[[:space:]]*$/d' "$AGENT_MODELS_FILE")
fi

echo
echo "============================================================"
echo "Installed models:"
echo "============================================================"
ollama list

echo
echo "Done. Try a model with:"
echo "  ollama run <model-name>"
