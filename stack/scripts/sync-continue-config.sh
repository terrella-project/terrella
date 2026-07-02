#!/usr/bin/env bash
# Regenerate the chat-tier section of a Continue config file from LiteLLM's
# live model list. By default it targets ./terrella-config.yaml in the current
# working directory. Preserves the autocomplete and embed model entries
# (anything NOT in the chat-tier block).
#
# How it works:
#   - Queries http://<host>:4000/models with the LiteLLM virtual key
#     (falls back to /v1/models for broader compatibility)
#   - Filters out embedding/autocomplete models (matched by name suffix)
#   - Rewrites the block between the markers below; everything else is kept
#
# Usage:
#   LITELLM_HOST=localhost LITELLM_KEY=sk-... ./sync-continue-config.sh
#   ./sync-continue-config.sh --host localhost --key sk-...
#   ./sync-continue-config.sh               # writes ./terrella-config.yaml
#   ./sync-continue-config.sh --dry-run     # print to stdout instead of writing
#   # When run from stack/, falls back to stack/.env -> LITELLM_EXPORTER_API_KEY
#
# Run on jupiter (or any client). Safe to re-run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$STACK_DIR/.env"
CONFIG="${CONTINUE_CONFIG:-$PWD/terrella-config.yaml}"
HOST="${LITELLM_HOST:-localhost}"
KEY="${LITELLM_KEY:-}"
PORT="${LITELLM_PORT:-4000}"
DRY_RUN=false

# Markers in the config file that bracket the auto-managed section.
BEGIN_MARKER="# >>> chat-tier models (managed by sync-continue-config.sh) >>>"
END_MARKER="# <<< chat-tier models <<<"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host) HOST="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --key)  KEY="$2"; shift 2 ;;
        --config) CONFIG="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        -h|--help)
            sed -n '2,18p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$KEY" && -f "$ENV_FILE" ]]; then
    # Use the read-only /models service key when available so the script can
    # run directly from stack/ without extra env setup.
    set -a
    source "$ENV_FILE"
    set +a
    KEY="${LITELLM_EXPORTER_API_KEY:-${LITELLM_KEY:-}}"
fi

if [[ -z "$KEY" ]]; then
    echo "ERROR: LiteLLM virtual key required (--key, LITELLM_KEY, or stack/.env LITELLM_EXPORTER_API_KEY)." >&2
    exit 1
fi

# Fetch live model list.
base_url="http://${HOST}:${PORT}"
api="${base_url}/models"
echo "Fetching models from $api..." >&2
json_tmp=$(mktemp)
trap 'rm -f "$json_tmp"' EXIT
if ! curl -fsS --max-time 10 "$api" -H "x-litellm-api-key: $KEY" -o "$json_tmp"; then
    api="${base_url}/v1/models"
    echo "Falling back to $api..." >&2
    curl -fsS --max-time 10 "$api" -H "Authorization: Bearer $KEY" -o "$json_tmp"
fi

# Generate the YAML block.
# Skip embed/autocomplete models — those stay hardcoded in the config.
generated=$(python3 - "$BEGIN_MARKER" "$END_MARKER" "$json_tmp" <<'PY'
import json, sys

begin, end, path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f:
    data = json.load(f)

# Filters: skip embeddings and the small autocomplete model.
def is_chat_tier(model_id: str) -> bool:
    lower = model_id.lower()
    if "embed" in lower or "nomic" in lower:
        return False
    if "1.5b" in lower:                  # autocomplete model
        return False
    if "tts" in lower or "image" in lower or "robotics" in lower:
        return False
    return True

# Group: anthropic, gemini, openai, ollama, other
def group(model_id: str) -> str:
    m = model_id.lower()
    if m.startswith("claude"):    return "Anthropic"
    if m.startswith("gemini"):    return "Gemini"
    if m.startswith("gpt"):       return "OpenAI"
    if m.startswith("ollama/"):   return "Local (ollama)"
    return "Other"

models = sorted({m["id"] for m in data.get("data", []) if is_chat_tier(m["id"])})

# Bucket
buckets: dict[str, list[str]] = {}
for mid in models:
    buckets.setdefault(group(mid), []).append(mid)

order = ["Anthropic", "Gemini", "OpenAI", "Local (ollama)", "Other"]
lines = [begin]
for grp in order:
    if grp not in buckets:
        continue
    lines.append(f"  # ── {grp} " + "─" * (66 - len(grp)))
    for mid in buckets[grp]:
        # Display name = the alias as-is.
        lines.append(f"  - name: {mid}")
        lines.append(f"    <<: *defaults")
        lines.append(f"    model: {mid}")
        lines.append(f"    <<: *chat_roles")
lines.append(end)
print("\n".join(lines))
PY
)

# Splice into the existing config: replace the lines between the markers.
# If markers are missing, insert the block at the top of `models:`.
# If the file does not exist yet, bootstrap a minimal Continue config.
if [[ ! -f "$CONFIG" ]]; then
    new_config=$(cat <<EOF
%YAML 1.1
---
name: Terrella
version: 1.0.0
schema: v1

defaults: &defaults
  provider: openai
  apiBase: http://${HOST}:${PORT}/v1
  apiKey: ""

chat_roles: &chat_roles
  roles: [chat, edit, apply]

models:
${generated}

  - name: qwen2.5-coder:1.5b (autocomplete)
    <<: *defaults
    model: ollama/qwen2.5-coder-1.5b
    roles: [autocomplete]
    autocompleteOptions:
      debounceDelay: 250
      maxPromptTokens: 1024

  - name: nomic-embed
    <<: *defaults
    model: ollama/nomic-embed
    roles: [embed]
EOF
)
elif grep -qF "$BEGIN_MARKER" "$CONFIG" && grep -qF "$END_MARKER" "$CONFIG"; then
    new_config=$(awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" -v block="$generated" '
        index($0, begin) > 0 {print block; in_block=1; next}
        index($0, end)   > 0 {in_block=0; next}
        !in_block            {print}
    ' "$CONFIG")
else
    # No markers yet — try to insert after the first occurrence of "models:".
    if ! grep -q "^models:" "$CONFIG"; then
        echo "ERROR: $CONFIG has no 'models:' section and no markers; cannot splice." >&2
        exit 1
    fi
    new_config=$(awk -v block="$generated" '
        /^models:/ && !done {
            print
            print block
            done=1; next
        }
        {print}
    ' "$CONFIG")
fi

if $DRY_RUN; then
    echo "----- generated config (dry run) -----"
    echo "$new_config"
    exit 0
fi

# Atomic write
mkdir -p "$(dirname "$CONFIG")"
tmp=$(mktemp)
echo "$new_config" > "$tmp"
mv "$tmp" "$CONFIG"
echo "Wrote $CONFIG"
