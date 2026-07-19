# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions will follow
[SemVer](https://semver.org/) once the `terrella` CLI ships (M1).

Every PR adds an entry under `[Unreleased]` (enforced by CI; the `no-changelog` label
exempts chores — see [docs/project-management.md](docs/project-management.md)).

## [Unreleased]

### Fixed

- **LiteLLM: billable background health checks disabled** (#95) —
  `background_health_checks: True` sent a real completion request to every
  `model_list` entry (~60 paid models) every 300 s and on every startup,
  ~15,000 paid API calls over 30 h; the `completion_model_health_check_*` keys
  from an earlier fix attempt are not real LiteLLM settings and did nothing.
  Liveness monitoring stays on the free `/health/liveness` endpoint
  (`litellm_exporter.py`); `GET /health` is also off-limits — with background
  checks off it live-probes every model on demand.
- **`firewall.sh`: reload before activating the new zone** — `--new-zone` only writes
  permanent config, so binding the interface and `--set-default-zone` failed with
  `INVALID_ZONE: terrella-lan` on first run (#10 follow-up).

### Changed

- **Docs updated for the Fedora + podman reality** (#14): maintenance.md backup/restore
  is podman-native (`podman volume export/import`, `podman exec pg_dump`, pinned-tag
  image updates); troubleshooting.md rewritten for rootless quadlets (systemctl --user,
  SELinux `:Z`, host-gateway, restored-volume ownership); cross-machine-access.md gains
  the earth node name, Fedora install steps, and the LAN-posture section;
  machines.md/tools.md reflect Fedora 44 + quadlets (no WSL distros); setup guide and
  stack/provision READMEs marked with the Fedora-primary / legacy-WSL split; stale
  clone paths updated in live docs (WSL-era setup pages keep theirs until #79).
- **Gaming toggle is now `systemctl --user stop terrella-inference.target`**
  (maintenance.md, #11): frees all model VRAM (measured 10.8 GB → 1.5 GB) while
  observability keeps running; `terrella.target` stops everything. Replaces the WSL-era
  `wsl --shutdown` / desktop-shortcut procedure; boot lands in AI Mode via lingering.

### Added

- **Fedora provisioning bootstrap** (`provision/fedora/bootstrap.sh` + runbook
  `docs/runbooks/fedora-provisioning.md`): idempotent detect→apply→verify for the quadlet
  stack's host prerequisites — NVIDIA open kernel modules (Blackwell), Secure Boot/MOK
  detection, nvidia-container-toolkit + CDI spec with regeneration on driver updates
  (toolkit refresh units or the `terrella-cdi-regen.service` fallback), podman, user
  lingering, Tailscale, and day-1 rootless-GPU/SELinux acceptance tests. Doubles as the
  behavioral spec for M1's fedora/dnf adapter (#4).
- **firewalld zone script** (`provision/fedora/firewall.sh`, #10): creates the
  `terrella-lan` zone — Fedora Workstation's service set **without** its default
  `1025-65535/tcp+udp` open range (which would expose host ollama to the LAN) — binds the
  LAN interface to it, and puts `tailscale0` in `trusted`. Loopback + tailnet are the only
  access paths; verification checklist included.
- **First persisted benchmark baseline** (#13): full local-model suite run on the
  migrated Fedora stack and recorded to `benchmark_results` (the table never existed on
  WSL — runs were silently unpersisted without psycopg2). Headlines: qwen2.5-coder:14b
  ≈ 98 t/s, the q2_K 32b variant ≈ 66 t/s inside 16 GB, full 32b confirms VRAM overflow
  (8 t/s). benchmarking.md gains the baseline table, Fedora prerequisites, and a note on
  the deepseek-r1 thinking-token measurement artifact (deferred to #29).
- **ollama as a systemd user service on Fedora** (`stack/quadlet/ollama.service`, #12):
  official release tarball under `~/.local` (no root install), `OLLAMA_HOST=0.0.0.0`
  carried over from the WSL drop-in pattern, member of `terrella-inference.target` so the
  gaming toggle frees its VRAM. Deliberate deviation from the issue's "host (system)
  service": a user unit lets one systemd manager own the whole stack. Model store copied
  from the WSL image (109 GB, #5) and pruned to `provision/models.list`, which gains the
  documented `qwen2.5-coder:32b-instruct-q2_K` 16 GB-VRAM variant.
- **terrella quadlet stack** (`stack/quadlet/`, #7): hand-written podman Quadlet units for
  all 8 services — the golden reference for M1's renderer (#18). Rootless under the login
  user; named `terrella` network with container-DNS-only inter-service config; every port
  published on loopback only; images pinned to exact version tags (no AutoUpdate);
  `terrella.target`/`terrella-inference.target` grouping; per-service `EnvironmentFile=`
  secrets split by `install.sh` (which also renders configs to `~/.config/terrella/`,
  links units, and pre-pulls images). Postgres/Grafana move from WSL-era bind mounts to
  named volumes; github-mcp updates to v1.x (streamable HTTP `/mcp` + per-request bearer
  auth, replacing SSE).
- **Quadlet networking pattern** (`stack/quadlet/README.md`, spike #6): containers reach
  host ollama at `http://host.containers.internal:11434` (pasta `--map-guest-addr`,
  measured working through firewalld); loopback-bound host listeners are unreachable
  (ollama keeps `OLLAMA_HOST=0.0.0.0`, LAN closed by firewalld); pasta does not hairpin
  published loopback ports, so inter-service config uses container DNS names only.
- **M0 data rescue runbook** (`docs/runbooks/fedora-migration.md`): offline extraction of
  the WSL-era stack data (secrets, Postgres dumps, volume tarballs, ollama models) from the
  old Windows install's mounted `ext4.vhdx` — no Windows boot required. Records the verified
  backups, baseline row counts, and two findings: Open WebUI's live store is the dedicated
  `openwebui` Postgres DB (resolves #8's investigation), and no WSL `benchmark_results`
  baseline ever existed (#13 will baseline against restored spend-log history) (#5).
- **Apache-2.0 LICENSE** and community health files: `CONTRIBUTING.md`, `SECURITY.md`
  (private vulnerability reporting), `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1),
  `.github/CODEOWNERS` (#53; ADR-0009).
- **REUSE/SPDX compliance**: whole-tree `REUSE.toml` + `LICENSES/`, `reuse lint` CI
  workflow (#58 — DCO remains deferred).
- **Supply-chain baseline**: OpenSSF Scorecard workflow + README badge, Dependabot for
  GitHub Actions, all workflow actions pinned to commit SHAs.
- **PyPI name reservation**: stub `terrella` package (`pyproject.toml` +
  `terrella/__init__.py`) and a Trusted Publishing release workflow
  (`.github/workflows/release.yml`); release process documented in
  `docs/operations/release.md` (advances #54).
- Root `.gitignore` (Python build artifacts, env files, generated configs).

- Roadmap (`ROADMAP.md`) with phases M0–M7: Fedora migration → terrella CLI → config/secrets/
  2026 models → observability v2 → agentic ops → benchmark-informed routing → OSS launch →
  multi-node.
- Architecture Decision Records in `docs/adr/` (ADR-0001…0007) covering the tool/platform
  end state, Podman+Quadlets runtime, the LiteLLM driver boundary, dual-platform support,
  multi-node interfaces, the config-in/artifacts-out principle, and the PM framework.
- GitHub-native project management: `docs/project-management.md`, declarative
  `.github/project.yml` + `scripts/project-sync.sh`, issue-form templates, PR template,
  path-based PR labeler, PR-title lint, and this changelog's CI check.
- Runbook for the Project board setup (`docs/runbooks/github-project-setup.md`).

### Changed

- **Project renamed from earth-ai to terrella** after a naming-collision review
  (ADR-0008); repo moved to `terrella-project/terrella`. All brand, CLI, config, and
  path references updated. Live infrastructure names (`Earth-AI` WSL distro, `earth-ai`
  tailnet hostname, the `earth-ai` compose project/volume prefix) deliberately keep
  their names until M0 retires them.
- Personal-deployment docs (machines, subscriptions, manual billing) moved from `docs/`
  to the new `deploy/earth/` overlay (start of the docs de-personalization split, #55).
- Continue.dev sync script output renamed to `terrella-config.yaml`.
- Added `docs/runbooks/rename-migration.md` (per-clone migration checklist).
- Repository transferred to a dedicated org under its new name.
- `README.md` / `AGENTS.md` updated for the project's new direction and earth's move to
  Fedora 44.
