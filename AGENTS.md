# Agent Instructions — terrella

This is a personal AI workstation repo evolving into an installable tool (`terrella`). Read `README.md`, `ROADMAP.md`, and `docs/01-overview.md` before making changes. Work tracking follows [`docs/project-management.md`](docs/project-management.md) (issue types, `component:*` labels, milestones M0–M7, conventional commits, CHANGELOG entry per PR); architectural decisions are ADRs in [`docs/adr/`](docs/adr/).

## Repo structure

| Path | Purpose |
|---|---|
| `ROADMAP.md` | Phases M0–M7, vision, sequencing and transition policy |
| `docs/` | All documentation — the canonical source of truth for the setup |
| `docs/adr/` | Architecture Decision Records |
| `docs/reference/` | Look-up docs: machines, models, subscriptions, tools, routing |
| `docs/setup/` | Numbered installation guide (01–07; WSL-era, migrating in M0) |
| `docs/operations/` | Day-2 ops: cross-machine access, maintenance, billing, troubleshooting |
| `docs/runbooks/` | Operator runbooks (GitHub project setup, rename migration, …) |
| `deploy/earth/` | The reference deployment overlay (machines, subscriptions, billing) — deployment-specific docs, not tool docs |
| `provision/` | `provision.sh` one-shot installer + `models.list` (legacy; absorbed by CLI in M1) |
| `stack/` | docker-compose: all services — Open WebUI, LiteLLM, Postgres, Prometheus, Grafana (legacy; quadlets in M0) |
| `stack/observability/` | config files for LiteLLM, Prometheus, and Grafana (mounted read-only) |
| `.github/project.yml` | Declarative PM spec (labels, milestones, board) — synced by `scripts/project-sync.sh` |

## Machines

Three machines; see [`deploy/earth/machines.md`](deploy/earth/machines.md) for full specs and prerequisites status.

- **earth** — primary workstation (i9-12900K, RTX 5080, 64 GB). **Now runs Fedora 44**; the old Windows 11 + WSL install remains bootable for taking data backups (M0). The machines doc still describes the WSL-era setup until the M0 docs pass.
- **jupiter** — laptop, mobile dev only, reaches earth via Tailscale.
- **Mac mini** — iOS dev (Xcode), same fallback as jupiter; potential Apple-silicon inference node at M7.

## Naming rules (do NOT "finish" the rename)

The project is **terrella** (formerly earth-ai; [ADR-0008](docs/adr/ADR-0008-project-name-terrella.md)).
These remaining `earth`/`earth-ai` names are **live infrastructure, not leftovers** — never rename them in docs or config:

- **`Earth-AI`** — the legacy WSL distro on the earth PC.
- **`earth-ai`** in URLs like `http://earth-ai:11434` — the Tailscale MagicDNS hostname.
- **`name: earth-ai`** in `stack/docker-compose.yml` — prefixes the live data volumes; renaming it orphans running Postgres/Grafana data (see the comment in that file).
- **`earth`**, **`jupiter`**, Mac mini — machine hostnames.

All of these retire with the M0 migration, deliberately.

## Doc conventions

- Cross-link between docs files using relative paths (e.g. `[machines.md](machines.md)`).
- **Placement rule:** generic tool documentation goes in `docs/`; anything specific to the reference deployment's machines, subscriptions, or billing goes in `deploy/earth/`.
- New files get REUSE/SPDX license metadata (covered repo-wide by `REUSE.toml`; add an SPDX header only if a file needs a different license than its directory default).
- Prerequisites and version info live in the tables in `deploy/earth/machines.md` — update that table when software is installed or upgraded.
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
