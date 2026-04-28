# `stack/`

All Earth AI runtime services in a single docker-compose project (`name: earth-ai`) running on the Earth-AI WSL distro.

| Service | Port | Purpose |
|---|---|---|
| `open-webui` | 8080 | Browser chat UI for humans. |
| `litellm` | 4000 | OpenAI-compatible API proxy. Logs every call. |
| `postgres` | 5433 | Backing store for LiteLLM + monthly subscription table. |
| `prometheus` | 9090 | Scrapes LiteLLM `/metrics`. Bound to localhost. |
| `grafana` | 3000 | Dashboards — AI Stack Overview. |

> **ollama is not in this folder.** It runs on the Earth-AI host (managed by systemd) on `localhost:11434`.

Config files mounted into containers live under [`observability/`](observability/).

## Quick start

```bash
cd ~/src/jomkz/earth-ai/stack
./scripts/generate-env.sh        # first time only — writes .env with random secrets
# Edit .env: fill in ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY
docker compose up -d
./scripts/init-billing-table.sh  # first time only — creates monthly_costs table
# → Open WebUI  http://127.0.0.1:8080
# → LiteLLM     http://127.0.0.1:4000
# → Grafana     http://127.0.0.1:3000
```

Full docs: [`../docs/setup/06-observability-stack.md`](../docs/setup/06-observability-stack.md)
