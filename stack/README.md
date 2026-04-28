# `stack/`

All Earth AI runtime services in a single docker-compose project (`name: earth-ai`) running on the Earth-AI WSL distro.

| Service | Port | Purpose |
|---|---|---|
| `open-webui` | 8080 | Browser chat UI for humans. Talks to ollama and optionally cloud providers. |
| `litellm` | 4000 | OpenAI-compatible API proxy for programs. Logs every call. |
| `postgres` | 5433 | Backing store for LiteLLM cost log + monthly subscription table. |
| `prometheus` | 9090 | Scrapes LiteLLM `/metrics`. Bound to localhost. |
| `grafana` | 3000 | Dashboards — AI Stack Overview. |

> **ollama is not in this folder.** It runs on the Earth-AI host (managed by systemd), reachable on `localhost:11434`. Services that need it connect via `network_mode: host`.

Config files live under [`observability/`](observability/) (litellm, prometheus, grafana provisioning).

## Quick start

```bash
cd ~/src/jomkz/earth-ai/stack
./scripts/generate-env.sh        # first time only — writes .env with random secrets
docker compose up -d
./scripts/init-billing-table.sh  # first time only — creates monthly_costs table
# → Open WebUI  http://127.0.0.1:8080
# → LiteLLM     http://127.0.0.1:4000
# → Grafana     http://127.0.0.1:3000
```

## Why two compose projects, not one?

- **Different lifecycles.** WebUI is a single image you `pull` on a whim. Observability has four services with secrets, a Postgres volume to back up, and a smoke test. Combining them would tangle one project's restarts with the other.
- **Different audiences.** WebUI is a UI you open in a browser. Observability is an API surface and a dashboard — programs talk to it, you only visit it to read graphs.
- **Different volumes.** Each project keeps its own named volume (`earth-ai_open-webui`, `observability_postgres-data`, …). Splitting projects keeps `docker volume ls` legible.

## Documentation

| Doc | Covers |
|---|---|
| [`../docs/setup/04-open-webui.md`](../docs/setup/04-open-webui.md) | First-run setup of WebUI |
| [`../docs/setup/06-observability-stack.md`](../docs/setup/06-observability-stack.md) | First-run setup of the observability project |
| [`../docs/operations/maintenance.md`](../docs/operations/maintenance.md) | Backup, restore, container updates |
| [`../docs/operations/manual-billing.md`](../docs/operations/manual-billing.md) | Logging Copilot / Claude monthly bills into Grafana |
| [`../docs/operations/troubleshooting.md`](../docs/operations/troubleshooting.md) | Common failure modes and fixes |
