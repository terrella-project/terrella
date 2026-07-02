# Roadmap

**earth-ai** is evolving from a personal AI-workstation blueprint (docs + scripts + compose)
into an installable, open-source tool: a CLI (working name **`earthai`**) that provisions and
manages a personal AI stack — local models, multi-provider gateway, cost ledger,
observability, and agentic operations — on any Linux box, config-driven. John's workstation
(**earth**, now Fedora 44) is the first deployment.

Work is tracked per [docs/project-management.md](docs/project-management.md): one GitHub
**milestone per phase** below, one **Epic** issue per milestone decomposed into sub-issues,
and the org Project board **earth-ai 1.0**. Architectural decisions are recorded as ADRs in
[docs/adr/](docs/adr/).

## Vision & principles

1. **Local first, paid for hard problems** — and always know what it costs.
2. **One validated config in, everything generated out** — user intent lives in
   `earthai.yaml`; quadlets, gateway config, dashboards, and timers are rendered artifacts
   ([ADR-0006](docs/adr/ADR-0006-config-in-artifacts-out.md)).
3. **The data layer is the product** — benchmark results + spend ledger + evals drive
   routing and agents; services are swappable drivers
   ([ADR-0003](docs/adr/ADR-0003-gateway-litellm-behind-driver-boundary.md)).
4. **Podman + Quadlets** — services are systemd units, rootless where possible
   ([ADR-0002](docs/adr/ADR-0002-podman-quadlets-runtime.md)).
5. **Multi-node-ready interfaces, single-node execution** until real hardware joins
   ([ADR-0005](docs/adr/ADR-0005-multi-node-interfaces-no-a2a.md)).

## Phases

Sizes are relative (S ≈ days, M ≈ weeks, L ≈ a month+ of part-time work).
**Current status: M0 in progress.**

| Phase | Goal | Size | Status |
|---|---|---:|---|
| **M0 — Fedora migration** | Full stack on Fedora 44 via hand-written quadlets; data restored from the WSL install; `earthai.target` replaces the `wsl --shutdown` gaming toggle | M | 🔄 active |
| **M1 — earthai CLI MVP** | `earthai provision && earthai apply` reproduces M0 from `earthai.yaml`; golden-file tests against the M0 quadlets; full CI matrix | L | ⬜ |
| **M2 — Config, secrets & 2026 models** | Gateway + serving fully config-rendered; podman secrets + sops-age; 2026 model refresh for 16 GB VRAM; DB migrations + `earthai_*` views | M | ⬜ |
| **M3 — Observability v2** | OTel GenAI tracing; Langfuse-vs-Phoenix spike; gateway-alternatives spike (TensorZero as potential M5 substrate) → ADRs | M | ⬜ |
| **M4 — Agentic ops v1** | `earthai mcp serve` stack-ops MCP server; systemd-timer agents (bench regression, spend report, catalog watcher) | L | ⬜ |
| **M5 — Benchmark-informed routing** | Task-class evals; routing advisor proposes `routing.yaml` as a PR with rationale; rendered into gateway config. The differentiator. | L | ⬜ |
| **M6 — OSS launch** | LICENSE (intended Apache-2.0), CONTRIBUTING, SECURITY, CoC, PyPI release pipeline, de-personalized docs | M | ⬜ |
| **M7 — Multi-node** | Platform-agnostic node agent, cross-node model placement, federated metrics, cluster copilot; A2A reassessment | L | ⬜ |

## Sequencing rules

- earth functional first (M0); refactors land before their dependents.
- Agents only consume existing CLI primitives — no bespoke plumbing per agent.
- Spikes are time-boxed and produce ADRs, not features.
- Multi-node has **zero code before M7**; only schema/config fields are node-aware earlier.
- Never two open Epics from different phases.

## Transition policy

- `stack/` (compose) and `provision/` (bash) remain the working reference through M0 and are
  the golden-file source for M1's renderer tests. They are deleted only after
  `earthai apply` reproduces them equivalently. **No new features land in the legacy scripts
  after M0.**
- The Windows/WSL path stays supported: WSL is a detection flag inside the debian
  provisioning adapter, not a separate platform
  ([ADR-0004](docs/adr/ADR-0004-dual-platform-distro-adapter.md)).
- Check PyPI/name availability for `earthai` at M1 scaffold time; final naming and licensing
  decisions land at M6.
