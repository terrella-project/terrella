# `stack/`

All Earth AI runtime services in a single docker-compose project (`name: earth-ai`) running on the Earth-AI WSL distro.

| Service | Port | Purpose |
|---|---|---|
| `open-webui` | 8080 | Browser chat UI for humans. |
| `litellm` | 4000 | OpenAI-compatible API proxy. Logs every call. |
| `litellm-exporter` | 11436 | Prometheus exporter for LiteLLM health and model-route count. |
| `github-mcp` | 8765 | GitHub MCP tool server (SSE). Registered in Open WebUI automatically. |
| `ollama-exporter` | 11435 | Prometheus exporter for host ollama loaded-model state. |
| `postgres` | 5433 | Backing store for LiteLLM + monthly subscription table. |
| `prometheus` | 9090 | Scrapes LiteLLM and ollama exporters. Bound to localhost. |
| `grafana` | 3000 | Dashboards — AI Stack Overview. |

> **ollama is not in this folder.** It runs on the Earth-AI host (managed by systemd) on `localhost:11434`.

Config files mounted into containers live under [`observability/`](observability/).

## Quick start

```bash
cd ~/src/jomkz/earth-ai/stack
./scripts/generate-env.sh        # first time only — writes .env with random secrets
# Edit .env: fill in ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, GITHUB_PAT
# Optional later: set LITELLM_EXPORTER_API_KEY to a read-only LiteLLM virtual key for /models route-count metrics
docker compose up -d
./scripts/init-billing-table.sh  # first time only — creates monthly_costs table
# → Open WebUI  http://127.0.0.1:8080
# → LiteLLM     http://127.0.0.1:4000
# → Grafana     http://127.0.0.1:3000
```

If you edit `stack/.env` later, use `docker compose up -d litellm litellm-exporter` to apply the new values. `docker compose restart` restarts the old containers without re-reading `.env`.

### GitHub MCP

`GITHUB_PAT` must be a classic PAT with `repo` and `read:org` scopes. Once the stack is up the tool server registers automatically via `TOOL_SERVER_CONNECTIONS` — no admin UI steps needed. Verify in Open WebUI: **Admin Panel → Settings → Tools** should show "GitHub" with status green.

Full docs: [`../docs/setup/06-observability-stack.md`](../docs/setup/06-observability-stack.md)
