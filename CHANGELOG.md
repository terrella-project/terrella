# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions will follow
[SemVer](https://semver.org/) once the `terrella` CLI ships (M1).

Every PR adds an entry under `[Unreleased]` (enforced by CI; the `no-changelog` label
exempts chores — see [docs/project-management.md](docs/project-management.md)).

## [Unreleased]

### Added

- **Evaluate local models per role** (#29) — `stack/scripts/eval-local-models.py` grades ollama
  models on the job each gateway role gives them, not only on speed: tab completion (fill a
  hole between a prefix and a suffix), reasoning (one checkable answer), summaries and log
  triage (required facts, no forbidden ones), coding (hidden tests in a sandbox container with
  no network), retrieval over this repo's docs, and an agent's tool loop at 64k. The task sets
  live in `stack/eval/`; `selfcheck` runs every answer key through the graders the models face.
  The tool guards its own failure modes: a model that spills off the GPU, shares the card, is
  cut off by the token limit, runs while the machine slept, or would load with too little free
  RAM is flagged, and the exit status says so. Results of the first run and the choices made
  from them: `docs/operations/model-refresh-2026-11.md`.
- **Gateway: a first route to neptune** (#99) — the gateway serves `neptune/llama3.2:3b`, a
  pinned name answered by neptune's ollama over the tailnet. It is the static second backend
  that ADR-0010 allows before the multi-node work of M7: one more entry in
  `stack/observability/litellm/config.yaml` with its own `api_base`. neptune is up without its
  GPUs, so this is one small model on the CPU that proves the path; no `local/` group points at
  neptune yet. `deploy/earth/machines.md` describes the machine as it now stands, with its first
  GPU baseline, and `docs/runbooks/neptune-provisioning.md` records what bring-up confirmed
  and corrected.
- **Grafana: the agents' credit pace** (#44) — two panels on the AI Stack Overview dashboard
  follow the `agents` team's budget cycle. One plots the team's spend this cycle against a
  straight line from nothing to its budget at the cycle's end. The other gives the spend, where
  the line stands now, and how far ahead of or behind it the team is. The cycle, the budget and
  the spend come from the team record and the ledger, so a change of budget or cycle needs no
  edit here. The weekly spend report that #44 asks for is a scheduled job of the agent runner.
- **Local agent lane** (#130) — the gateway serves `local/agent`, a local model that an agent
  harness speaking the Anthropic Messages format can run its tool loop against. The entry
  presents ollama's own `/v1/messages` endpoint to LiteLLM as an `anthropic` endpoint, so the
  gateway adds keys, model lists and the ledger and translates nothing. New
  `provision/agent-models.list` names each agent model with its context size, and
  `provision/sync-models.sh` creates the `<model>-<N>k` variant from it (the same weights, no
  second download): agent tools need 64k or more, and ollama's default on a card under 24 GiB is
  4k. First model: `ornith-1.5:9b` at 64k.
- **Gateway: Claude 5 models** (#128) — the Anthropic catalog in
  `stack/observability/litellm/config.yaml` is regenerated from the provider's model list:
  Fable 5 / 5.1 / 5.2, Opus 4.8 / 5 / 5.5, Sonnet 5 / 5.5 and Haiku 5.5 are added and the
  retired Opus 4.1 is gone. New `claude-fable` alias for Fable 5.2.
- **CI: `auto-close-epics` workflow** — backported from `mkzsystems/pm-framework`; closes a parent epic when its last sub-issue closes (predicate matches the Epic issue type or the `epic` label).
- **ADR-0010 — Neptune as the future primary node (deferred)** — records the intended
  topology (neptune, 4× MI100, becomes the always-on inference heart; earth demotes to an
  opportunistic fast/dev node), a scoped pre-M7 static-routing carve-out on ADR-0005, and
  the gfx908 serving stance. No code; hardware is still in build.
- **`docs/runbooks/neptune-provisioning.md`** (draft) — back-pocket bring-up checklist
  (cooling/power/BIOS, Fedora+ROCm, ollama-first serving, network parity, benchmark baseline).
- **Model-naming convention in `docs/reference/routing.md`** — `local/<model>` routed groups
  vs pinned `earth/<model>` / `neptune/<model>`, adopted now so no rename is needed when a
  second serving node comes online.
- **`deploy/earth/machines.md`** gains **luna** (iPhone client) and a **Planned: neptune**
  entry; Mac mini is named **mercury**.

### Changed

- **ollama has a memory ceiling** (#138) — `stack/quadlet/ollama.service` sets `MemoryHigh=12G`,
  `MemoryMax=16G` and `MemorySwapMax=0`. The unit's cgroup is charged for the page cache of every
  model file ollama reads, and on 2026-11-27 it reached 33 GB. earth ran out of memory, zram
  filled, and the desktop froze until the kernel killed ollama. Now a load that needs more than
  the ceiling gets ollama, and only ollama, killed and restarted. With the current catalog the
  unit peaks near 10 GB. `docs/operations/troubleshooting.md` says how to tell the ceiling hit
  and when to raise it.
- **Gateway: local models by role** (#29) — clients ask for `local/fim`, `local/general`,
  `local/reason`, `local/code` or `local/embed` (beside `local/agent`), and the gateway decides
  which model serves each: `qwen2.5-coder:3b`, `nemotron-3.5-bolt:e4b` for both summaries and reasoning, `gemma4:12b` with
  thinking off, and `embeddinggemma-2`, each chosen from measurements. The Continue example and
  `sync-continue-config.sh` use the role names, which also fixes the embed entry: it named
  `ollama/nomic-embed`, which the gateway never served. `local/embed`'s new model means
  Continue rebuilds its codebase index once. The `ollama/<model>` catalog block is now generated
  from `provision/models.list` rather than from whatever the machine has pulled, and
  `benchmark-models.py` benchmarks the `local/` roles by default.
- **Gateway: the Claude tier aliases follow the current models** (#128) — `claude-opus`,
  `claude-sonnet` and `claude-haiku` now reach Opus 5.5, Sonnet 5.5 and Haiku 5.5, where
  they reached Opus 4.7, Sonnet 4.6 and Haiku 4.5. A client that calls an alias gets the
  newer model and its price. The `model_aliases` lines on those entries are removed: it is
  not a LiteLLM setting, and the names it listed were never served.
- **Public-readiness scrub of personal identifiers** (ahead of the M6 OSS launch): clone
  paths genericized to `~/src/terrella`, literal usernames in the fedora-migration runbook
  replaced with `<user>`, "John's …" prose reworded to "the reference/maintainer's …"
  (deliberate license/package attribution kept), sibling-repo names/links and org-lineage
  references removed from the PM docs and ADRs, and jupiter hardware fingerprints trimmed.
- **`machines.md` Tailscale status reconciled** — earth's row now reflects the live
  `tailscale serve` state (11434 / 4000 / 3000) instead of the stale "pending".

### Removed

- **The 2025 local models and their aliases** (#29) — `qwen2.5-coder:1.5b`, `gemma2:9b` and
  `deepseek-r1:14b` leave `provision/models.list`, and the gateway no longer serves the `deepseek`,
  `gemma2`, `qwen2.5-coder`, `qwen2.5-coder-15b` and `nomic-embed` aliases. Nothing had called
  them through the gateway since July 2026. `qwen2.5-coder:14b` stays, pinned by name, because
  fighters-legacy measured its AI features against it. The inert `model_aliases` lines left on
  the OpenAI entries go too: the setting does nothing in LiteLLM.
- **Thirteen old local models** (#29) — `provision/models.list` drops `qwen2.5-coder:32b`,
  `qwen2.5-coder:32b-instruct-q2_K` and its whole general-purpose, coding and lightweight
  sets (`llama3.1`, `llama3.2`, `mistral`, `mixtral`, `qwen2`, `qwen2.5`, `codellama`,
  `deepseek-coder`, `phi3`, `gemma`, `tinyllama`): about 90 GB. The gateway no longer serves
  `qwen2.5-coder-32b`, `qwen2.5-coder-32b-instruct` or their `ollama/` catalog names, and the
  docs and the Continue example stop offering them. Nothing had called any of the thirteen
  through the gateway since July 2026, and the full 32b does not fit a 16 GB card. `deepseek-r1:14b`, `gemma2:9b` and `qwen2.5-coder:1.5b` stay until the
  general re-benchmark picks their replacements. Removing a line does not remove the model:
  run `ollama rm` for each.

### Fixed

- **ollama can restart while Tailscale runs** (#134) — the docs told you to add a
  `tailscale serve` entry for 11434. Its listener can never bind while ollama holds
  `0.0.0.0:11434`, but it takes the port when ollama stops, so after the out-of-memory kill of
  2026-11-27 every restart failed with "address already in use". ollama needs no serve entry:
  `tailscale0` is in the `trusted` zone, so the tailnet reaches its own listener. The entry is
  dropped from `docs/operations/cross-machine-access.md`, `deploy/earth/machines.md` and the
  neptune runbook, and they say why. ollama keeps `0.0.0.0`, because containers reach the host
  only on its LAN address.
- **Tab completion through the gateway sees the code after the cursor** (#29) — LiteLLM's
  `ollama/` provider sends a completion's `suffix` inside `options`, where ollama's
  `/api/generate` ignores it, so every gateway FIM request was a plain continuation of the
  prefix. `local/fim` now goes through ollama's OpenAI-compatible `/v1/completions`, which takes
  `suffix` as a field (checked with a recording stand-in for ollama).
- **`provision/agent-models.list` gives `ornith-1.5:9b`'s real GPU memory** (#29) — 8.5 GB
  at 64k by `nvidia-smi`, where it gave ollama's 7.7 GB; `ollama ps` under-reports it.

- **Gateway: sampling parameters no longer break calls to newer Claude models** (#128) —
  every Claude model from Opus 4.7 on answers a request that sets `temperature`, `top_p` or
  `top_k` with a 400, and `drop_params` does not cover that on LiteLLM 1.83.14. Those
  entries now carry `additional_drop_params`, which `update-litellm-config.sh` writes for
  the catalog. This covers the OpenAI-format routes; `/v1/messages` passes a request through
  unchanged, so a client of that route still gets the provider's 400.
- **`update-litellm-config.sh` leaves an up-to-date file unchanged** (#128) — each run added
  one more comment line above the catalog marker and removed the file's final newline.
- **Gateway: the `gpt` alias loads** (#128) — its `model` had no provider prefix
  (`gpt-5-5`), so LiteLLM skipped the entry at every start with "LLM Provider NOT provided".
- **Dependabot PRs no longer fail the changelog check** — `.github/dependabot.yml`
  now applies the `no-changelog` label to its PRs (dependency bumps are chores with no
  user-facing change), so they stop tripping the enforced-CHANGELOG gate.
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
