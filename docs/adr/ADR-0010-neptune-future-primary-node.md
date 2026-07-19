# ADR-0010 — Neptune as the future primary node (deferred)

**Date:** 2026-07-19 · **Status:** Proposed (deferred — hardware in build)

## Context

The stack today is single-node on **earth** (Fedora 44, RTX 5080 16 GB). Earth dual-boots
Windows for gaming, so it is not truly always-on, and 16 GB caps local models at roughly
14B (8-bit) / 30B (aggressive 4-bit).

A dedicated inference rig — **neptune**, 4× AMD Instinct MI100 (32 GB HBM2 each = 128 GB
total, gfx908 / CDNA 1, ROCm) — is being built to become the always-on heart of the system:
capacity for 70B–120B-class models, aggregate throughput for concurrent agent work, and an
uptime earth cannot offer. This ADR records the intended topology and the decisions worth
settling now, **so they are not re-litigated at bring-up**. It changes no code and starts no
work: neptune does not exist yet, and [ADR-0005](ADR-0005-multi-node-interfaces-no-a2a.md)
keeps full multi-node machinery at M7.

## Decision

Recorded as intent; execution is deferred until neptune is built.

- **Topology.** Neptune becomes the primary node — gateway (LiteLLM), state (Postgres),
  Open WebUI, observability, and the M4 timer agents migrate there; earth demotes to an
  *opportunistic* fast-inference + development node. Until neptune is online, **earth remains
  primary** and nothing changes.

- **Scoped amendment to ADR-0005.** When neptune arrives, *statically-configured*
  second-backend routing is permitted **before M7**: extra LiteLLM deployments carrying a
  per-node `api_base`, with cooldown-on-connection-error and **no background health checks**
  (background checks bill real completions — see [#96]). The node agent, `nodes`/`node_models`
  DB registration, dynamic placement, and Prometheus federation remain M7. *Static config is
  the guardrail*: if pre-M7 work starts growing registration or health-probe machinery, that
  is M7 leaking backward and should stop.

- **Serving engine on gfx908: ollama-first.** ollama's ROCm build bundles its own ROCm
  userspace, so the host needs only the in-tree `amdgpu` driver — which keeps Fedora parity
  viable even though AMD officially blesses ROCm on Ubuntu/RHEL, not Fedora. `llama.cpp`
  server (HIP) and a community `vllm-rocm-gfx908` image are **time-boxed spikes**, not
  commitments (official vLLM targets gfx90a/gfx942+). Pin serving-engine versions in
  `terrella.yaml` — gfx908 is deprecated-tier and its kernel support may decay. gfx908 has
  **no flash-attention**, so long-context prompt processing is the number to benchmark
  before committing primacy.

- **Routing / failover.** `local/*` model groups span both nodes, weighted toward the
  always-on neptune; earth's deployment cools down on connection-refused (i.e. when it is in
  Windows / gaming), and requests transparently retry on neptune. Models too large for
  earth exist only as `neptune/*` deployments and hard-fail if neptune is down — which is
  correct. Cloud `fallbacks: []` stays deliberate and untouched. The naming convention
  (`local/*` routed groups, `earth/*` / `neptune/*` pinned) is documented in
  [routing.md](../reference/routing.md) and adopted now so no rename is needed later.

- **Migration order (a future, M2.5-shaped epic).** Secrets first (podman secrets + sops-age,
  M2 #27) so env files are not hand-copied and redone; then `pg_dump`/restore both DBs
  (same Postgres major, same `LITELLM_SALT_KEY` carried via sops so the spend ledger and
  virtual keys survive); then flip LiteLLM / Open WebUI / observability; then repoint
  `tailscale serve` and re-render client configs; then retire earth's units. One-evening
  cutover; rollback = re-enable earth's units.

## Consequences

- **M1 (CLI) is unchanged and becomes more valuable** — the renderer is exactly what will
  emit per-host artifacts. The only ask: keep `terrella.yaml`'s top level shaped so a
  `hosts:` concept can be added later without breaking the M0 golden files (do not hardcode
  `earth` into rendered paths/names).
- Near-term "farm agent work to the other devices" targets **earth only** and needs no
  neptune: gateway virtual keys per client, Open WebUI over `tailscale serve` for luna, and
  `tailscale ssh` + tmux agent sessions on earth. Tracked as issues on the existing
  M2/M3 epics.
- The bring-up checklist lives in
  [neptune-provisioning.md](../runbooks/neptune-provisioning.md) so it is ready when the
  hardware is.
- **Risk:** if the gfx908 prompt-processing benchmark disappoints, the fallback posture is
  "neptune = big-model + always-on host, earth = fast path" — which this design already
  supports through the pinned `earth/*` / `neptune/*` names. No decision here forecloses it.

[#96]: https://github.com/terrella-project/terrella/issues/96
