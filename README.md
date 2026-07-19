# 🌍 Terrella — Personal AI Stack

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/terrella-project/terrella/badge)](https://scorecard.dev/viewer/?uri=github.com/terrella-project/terrella)

A *terrella* ("little Earth") is the small magnetized model of Earth that early scientists ran lab experiments on. This one is a homelab-scale AI stack — born on a desktop PC named **earth** ([ADR-0008](docs/adr/ADR-0008-project-name-terrella.md) has the naming story).

A reproducible setup for a personal AI workstation — **Fedora Linux (primary) or WSL2/Ubuntu (supported)** with an NVIDIA RTX 5080 — running local LLMs (via [ollama](https://ollama.com)) for everyday coding, with paid cloud APIs (Anthropic / Gemini / OpenAI) reserved for hard problems. Every API call is logged to Postgres and visualized in Grafana, so total spend across local + paid services is always one chart away.

## 🧭 Direction & roadmap

This project is evolving from a workstation blueprint into an **installable open-source tool** — a `terrella` CLI that provisions and manages a personal AI stack on any Linux box, running on Podman + Quadlets, with a multi-node homelab as the end state. The plan lives in [ROADMAP.md](ROADMAP.md) (phases M0–M7), architectural decisions in [docs/adr/](docs/adr/), and work tracking in [docs/project-management.md](docs/project-management.md).

> **Transition note:** earth (the reference machine) now runs Fedora 44; the docs below still describe the WSL-era setup and are being migrated as part of [M0](ROADMAP.md#phases). The `stack/` and `provision/` trees remain the working reference until the CLI reproduces them (see the transition policy in ROADMAP.md).

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
   cd ~/src/terrella
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
| Log this month's Copilot / Claude bill | [deploy/earth/manual-billing.md](deploy/earth/manual-billing.md) |
| Something broke | [docs/operations/troubleshooting.md](docs/operations/troubleshooting.md) |
