# `stack/`

The runtime services that make up Earth AI's "stack" — two independent docker-compose projects that run side-by-side on the Earth-AI WSL distro.

| Project | Purpose | Compose project name |
|---|---|---|
| [`webui/`](webui/) | **Open WebUI** — browser chat UI for humans. Talks to ollama (and optionally cloud providers configured in its settings). | `earth-ai` |
| [`observability/`](observability/) | **LiteLLM + Postgres + Prometheus + Grafana** — OpenAI-compatible API proxy for programs, with per-call cost logging and dashboards. | `observability` |

> **ollama itself is not in this folder.** It runs on the Earth-AI host (managed by systemd), reachable on `localhost:11434`. Both compose projects above connect to it through `network_mode: host`.

## Quick start

```bash
# Open WebUI (chat for humans):
cd ~/src/jomkz/earth-ai/stack/webui
docker compose up -d
# → http://127.0.0.1:8080

# Observability (proxy + dashboards for programs):
cd ~/src/jomkz/earth-ai/stack/observability
./scripts/generate-env.sh        # first time only
docker compose up -d
./scripts/init-billing-table.sh  # first time only
# → LiteLLM http://127.0.0.1:4000
# → Grafana  http://127.0.0.1:3000
```

The two projects are independent: you can run either one without the other. They share nothing except the underlying ollama on `localhost:11434`.

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
