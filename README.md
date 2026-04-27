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
| [docs/operations/](docs/operations/) | Day-2: cross-machine (Tailscale) access, backups, gaming toggle, monthly billing entry, troubleshooting. |

## Repo contents

| Path | Purpose |
|---|---|
| [`docs/`](docs/) | All documentation. |
| [`provision/`](provision/) | One-shot installer (`provision.sh`) and the list of ollama models it pulls (`models.list`). |
| [`stack/webui/`](stack/webui/) | docker-compose project: **Open WebUI** (chat UI). |
| [`stack/observability/`](stack/observability/) | docker-compose project: **LiteLLM + Postgres + Prometheus + Grafana** (API proxy + dashboards). |

## Quickstart for a fresh install

1. On Windows: install the NVIDIA driver, `wsl --install -d Ubuntu-24.04`, create `%UserProfile%\.wslconfig` (template in [docs/setup/01-windows-host.md](docs/setup/01-windows-host.md)), then `wsl --shutdown`.
2. In WSL: clone this repo and run the provisioner:
   ```bash
   cd ~/src/jomkz/earth-ai
   bash provision/provision.sh
   ```
   Details: [docs/setup/README.md](docs/setup/README.md).
3. Bring up Open WebUI:
   ```bash
   cd stack/webui && docker compose up -d
   ```
   → open <http://127.0.0.1:8080>.
4. Optionally bring up the observability stack: [docs/setup/06-observability-stack.md](docs/setup/06-observability-stack.md).

## Already set up — common tasks

| Task | Doc |
|---|---|
| Pick a model for the task at hand | [docs/reference/routing.md](docs/reference/routing.md) |
| Use the workstation from jupiter / Mac mini | [docs/operations/cross-machine-access.md](docs/operations/cross-machine-access.md) |
| Stop everything before launching a game | [docs/operations/maintenance.md#gaming-toggle](docs/operations/maintenance.md#gaming-toggle) |
| Back up Open WebUI chats | [docs/operations/maintenance.md#backup--restore-open-webui](docs/operations/maintenance.md#backup--restore-open-webui) |
| Log this month's Copilot / Claude bill | [docs/operations/manual-billing.md](docs/operations/manual-billing.md) |
| Something broke | [docs/operations/troubleshooting.md](docs/operations/troubleshooting.md) |
