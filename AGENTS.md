# Agent Instructions — earth-ai

This is a personal AI workstation documentation and configuration repo. Read `README.md` and `docs/01-overview.md` before making changes.

## Repo structure

| Path | Purpose |
|---|---|
| `docs/` | All documentation — the canonical source of truth for the setup |
| `docs/reference/` | Look-up docs: machines, models, subscriptions, tools, routing |
| `docs/setup/` | Numbered installation guide (01–07) |
| `docs/operations/` | Day-2 ops: cross-machine access, maintenance, billing, troubleshooting |
| `provision/` | `provision.sh` one-shot installer + `models.list` |
| `stack/` | docker-compose: all services — Open WebUI, LiteLLM, Postgres, Prometheus, Grafana |
| `stack/observability/` | config files for LiteLLM, Prometheus, and Grafana (mounted read-only) |

## Machines

Three machines; see [`docs/reference/machines.md`](docs/reference/machines.md) for full specs and prerequisites status.

- **earth** — primary workstation (Windows 11, i9-12900K, RTX 5080, 64 GB). Two WSL distros: `Earth-AI` (AI services) and `Ubuntu-24.04` (dev workspace).
- **jupiter** — laptop, mobile dev only, reaches earth via Tailscale.
- **Mac mini** — iOS dev (Xcode), same fallback as jupiter.

## Doc conventions

- Cross-link between docs files using relative paths (e.g. `[machines.md](machines.md)`).
- Prerequisites and version info live in the tables in `docs/reference/machines.md` — update that table when software is installed or upgraded.
- `_TODO_` is the placeholder for not-yet-gathered info in tables.
- Installed tool versions go in [`docs/reference/tools.md`](docs/reference/tools.md).
- Local model list is maintained in [`docs/reference/local-models.md`](docs/reference/local-models.md) and `provision/models.list`.

## Key ports (Earth-AI WSL)

| Service | Port |
|---|---|
| ollama | 11434 |
| Open WebUI | 8080 |
| LiteLLM | 4000 |
| Postgres | 5433 |
| Prometheus | 9090 |
| Grafana | 3000 |
