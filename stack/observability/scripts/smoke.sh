#!/usr/bin/env bash
# End-to-end probe: send a tiny chat to ollama via the LiteLLM proxy.
# Confirms LiteLLM is up, can reach ollama, and is logging spend.
#
# Requires a virtual API key — create one in the LiteLLM admin UI at
# http://localhost:4000/ui (login with $LITELLM_MASTER_KEY) and pass it as $1
# or via env LITELLM_KEY.

set -euo pipefail

key="${1:-${LITELLM_KEY:-}}"
if [[ -z "$key" ]]; then
    echo "Usage: $0 <virtual-key>   (or set LITELLM_KEY)" >&2
    exit 1
fi

curl -fsS http://localhost:4000/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $key" \
    -d '{
        "model": "ollama/qwen2.5-coder-14b",
        "messages": [{"role": "user", "content": "Say hello in exactly three words."}],
        "max_tokens": 16
    }' | python3 -m json.tool

echo
echo "Open http://localhost:3000 → AI Stack Overview to see the call appear."
