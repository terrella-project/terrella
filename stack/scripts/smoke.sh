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

# 1. Health check
echo "Checking LiteLLM health..."
curl -fsS --max-time 5 http://localhost:4000/health/liveness | python3 -m json.tool

# 2. Chat completion (allow up to 120s — first call loads model into VRAM)
echo
echo "Sending test chat (may take up to 120s on first run while model loads)..."
response=$(curl -sS --max-time 120 \
    -w "\n%{http_code}" \
    http://localhost:4000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $key" \
    -d '{
        "model": "ollama/qwen2.5-coder-14b",
        "messages": [{"role": "user", "content": "Say hello in exactly three words."}],
        "max_tokens": 16
    }')

http_code=$(tail -1 <<< "$response")
body=$(head -n -1 <<< "$response")

if [[ "$http_code" != "200" ]]; then
    echo "ERROR: HTTP $http_code" >&2
    echo "$body" | python3 -m json.tool >&2
    exit 1
fi

echo "$body" | python3 -m json.tool
echo
echo "OK — open http://localhost:3000 → AI Stack Overview to see the call appear."
