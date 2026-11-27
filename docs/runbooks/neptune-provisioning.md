# Runbook — neptune bring-up (in progress)

> **Status: in progress.** neptune (the 4× MI100 AMD/ROCm inference rig) is up and the gateway
> has its first pinned route to it, but its GPUs are out of the machine until ducted airflow is
> built, so it serves on the CPU only. Where it stands is in
> [machines.md](../../deploy/earth/machines.md#neptune-second-serving-node). Multi-node is
> still M7 by [ADR-0005](../adr/ADR-0005-multi-node-interfaces-no-a2a.md); the intended role
> and the pre-M7 static-routing carve-out are recorded in
> [ADR-0010](../adr/ADR-0010-neptune-future-primary-node.md). The checklist below was written
> before the hardware existed. Where bring-up confirmed or corrected a step, a note marked
> **Found** says so.

## Hardware first

- **Cooling is the #1 homelab risk.** MI100s are passively cooled server cards — they expect
  ducted chassis airflow. Plan aftermarket shrouds/fans before powering on under load.
  **Found (2026-08-20):** not only under load. In an open tower case with only the case fans,
  three cards reached 98–105 °C junction at idle draw. The ducting comes before the cards go
  in, and a thermal watchdog runs on the node: it stops ollama at 92 °C junction and powers
  the machine off at 100 °C.
- **Power:** size the PSU for 4× ~300 W TDP plus the rest of the box (~1.2 kW under load);
  account for idle draw of four server GPUs when the rig is always-on.
  **Found (2026-08-19):** slot power matters as much as the PSU's size. With three or more
  cards the board's auxiliary PCIe power connector must be fed, and from a cable of its own.
  Starved slot power looked exactly like failing GPUs: a card that would not train its PCIe
  link, and compute hangs under load.
- **BIOS:** enable **Above-4G Decoding** and **Resizable BAR**; confirm PCIe lane allocation
  across the four cards.

## OS & ROCm

- **OS:** Fedora 44 for parity with earth (reuses `provision/fedora/bootstrap.sh`, the quadlet
  patterns, and the [ADR-0004](../adr/ADR-0004-dual-platform-distro-adapter.md) distro
  adapter). This is viable **because ollama's ROCm build bundles its own ROCm userspace** —
  the host needs only the in-tree `amdgpu` kernel driver. If gfx908 proves painful, fall back
  to **Ubuntu 24.04 LTS** (an officially supported ROCm target; Debian and Fedora are not).
  **Found (2026-08-19):** it holds. ollama's ROCm release tarballs run gfx908 on Fedora 44
  with nothing but the in-tree `amdgpu` driver on the host.
- **GPU plumbing (AMD, no CDI needed):** add the login user to `video` + `render` groups;
  confirm `/dev/kfd` and `/dev/dri/renderD*` exist. If serving is ever containerized, the
  quadlet uses `AddDevice=/dev/kfd` + `AddDevice=/dev/dri` — simpler than earth's nvidia CDI
  path.

## Serving

- ollama ROCm tarball + a neptune `ollama.service` mirroring
  [stack/quadlet/ollama.service](../../stack/quadlet/ollama.service):
  `OLLAMA_HOST=0.0.0.0`, `OLLAMA_SCHED_SPREAD=1` so 70B+ models split across the four GPUs.
  **Found (2026-08-19):** also set `OLLAMA_CONTEXT_LENGTH`. ollama's default context follows
  the VRAM it sees, reached 262144 here, and quietly left a quarter of a 70B model's layers on
  the CPU (2 tokens/s). neptune pins 8192; a request raises it with `num_ctx`.
- **Later optimization (optional):** multiple ollama instances pinned via
  `ROCR_VISIBLE_DEVICES` on ports 11434–11437 (e.g. coder on GPU0, a 70B across GPU1–2,
  embeddings on GPU3), each a separate LiteLLM deployment.
- **Spikes (time-boxed, per ADR-0010):** `llama.cpp` server (HIP, `--split-mode row`) and a
  community `vllm-rocm-gfx908` image for batch/agent throughput. Record **prompt-processing**
  tok/s as well as decode — gfx908 has no flash-attention, so prompt processing on long
  contexts is the number that decides whether neptune is the agent heart or the big-model
  host.

## Network parity with earth

- firewalld `terrella-lan` zone (block the LAN default range that would expose
  `0.0.0.0:11434`); trust `tailscale0`.
- `tailscale up --ssh`; `tailscale serve` for 11434 (ollama), 4000 (LiteLLM once it lives
  here), and 443→8080 (Open WebUI PWA for luna).

## Register in the stack

- Add `hosts.neptune` to `terrella.yaml`; render with `terrella provision --host neptune`
  (schema/CLI work — do not start before it is needed).
- Add neptune deployments to the LiteLLM config (per-node `api_base`; see the routing
  convention in [routing.md](../reference/routing.md)).
  **Done for a first route (2026-11-27):** `neptune/llama3.2:3b`, a small model on the CPU,
  reached by neptune's tailnet name. The GPU models follow the cards.
- Smoke test, then record a per-model tok/s **benchmark baseline** — it feeds the primacy
  decision (ADR-0010) and later benchmark-informed routing (M5).
  **A first baseline exists (2026-08-19)**, from two cards capped at 200 W each; it is in
  [machines.md](../../deploy/earth/machines.md#neptune-second-serving-node). The full one
  waits for all four cards at full power.

## Docs to update at bring-up

- Fill in [deploy/earth/machines.md](../../deploy/earth/machines.md) → the "Planned: neptune"
  section with real specs and status. **Done (2026-11-27):** it is now
  "neptune (second serving node)".
- Add the two-tier model catalog (neptune tier vs earth tier) to
  [local-models.md](../reference/local-models.md).
