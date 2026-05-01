# 🌍 Project Earth — Universal AI Workstation

A reproducible setup for a personal AI workstation — Windows 11 host + WSL2 + NVIDIA RTX 5080 — running local LLMs (via [ollama](https://ollama.com)) for everyday coding, with paid cloud APIs (Anthropic / Gemini / OpenAI) reserved for hard problems. Every API call is logged to Postgres and visualized in Grafana, so total spend across local + paid services is always one chart away.

```
Open WebUI (chat for humans)  ──┐
                                ├──►  ollama  ──►  RTX 5080
LiteLLM (proxy for programs)  ──┘     :11434
       │
       ├─►  Anthropic / Gemini / OpenAI  (per-call cost logged)
       └─►  Postgres → Grafana          (one dashboard, all spend)
```

## 📚 Full documentation: [`docs/`](docs/README.md)

The whole guide lives under `docs/` and is structured for someone building this from scratch.

| Section | What's inside |
|---|---|
| [docs/01-overview.md](docs/01-overview.md) | Architecture, glossary, and what's in the repo. **Start here.** |
| [docs/setup/](docs/setup/) | Six-phase installation guide (Windows host → WSL → ollama → Open WebUI → Aider → observability stack). |
| [docs/reference/](docs/reference/) | Look-up docs: machines, installed models, subscriptions, per-tool inventory, and the **model-routing decision table**. |
| [docs/operations/](docs/operations/) | Day-2: cross-machine (Tailscale) access, backups, gaming toggle, model benchmarking, monthly billing entry, troubleshooting. |

## Repo contents

| Path | Purpose |
|---|---|
| [`docs/`](docs/) | All documentation. |
| [`provision/`](provision/) | Machine provisioner (`provision.sh`), model manager (`sync-models.sh`), and the model catalog (`models.list`). Run them independently. |
| [`stack/`](stack/) | docker-compose project: all runtime services — **Open WebUI + LiteLLM + Postgres + Prometheus + Grafana**. Config files mounted into containers live under [`stack/observability/`](stack/observability/). |

## Quickstart for a fresh install

1. On Windows: install the NVIDIA driver, `wsl --install -d Ubuntu-24.04`, create `%UserProfile%\.wslconfig` (template in [docs/setup/01-windows-host.md](docs/setup/01-windows-host.md)), then `wsl --shutdown`.
2. In WSL: clone this repo and run the provisioner:
   ```bash
   cd ~/src/jomkz/earth-ai
   bash provision/provision.sh
   ```
   Details: [docs/setup/README.md](docs/setup/README.md).
3. Bring up the full stack:
   ```bash
   cd stack
   ./scripts/generate-env.sh   # first time only — writes .env with random secrets
   docker compose up -d
   ./scripts/init-billing-table.sh   # first time only — creates monthly_costs table
   ./scripts/init-benchmark-table.sh # first time only — creates benchmark_results table
   ```
   → Open WebUI <http://127.0.0.1:8080> · LiteLLM <http://127.0.0.1:4000> · Grafana <http://127.0.0.1:3000>.

## Already set up — common tasks

| Task | Doc |
|---|---|
| Pick a model for the task at hand | [docs/reference/routing.md](docs/reference/routing.md) |
| Use the workstation from jupiter / Mac mini | [docs/operations/cross-machine-access.md](docs/operations/cross-machine-access.md) |
| Measure how fast local models run (tok/s, TTFT, VRAM) | [docs/operations/benchmarking.md](docs/operations/benchmarking.md) |
| Stop everything before launching a game | [docs/operations/maintenance.md#gaming-toggle](docs/operations/maintenance.md#gaming-toggle) |
| Back up Open WebUI chats | [docs/operations/maintenance.md#backup--restore-open-webui](docs/operations/maintenance.md#backup--restore-open-webui) |
| Log this month's Copilot / Claude bill | [docs/operations/manual-billing.md](docs/operations/manual-billing.md) |
| Something broke | [docs/operations/troubleshooting.md](docs/operations/troubleshooting.md) |
