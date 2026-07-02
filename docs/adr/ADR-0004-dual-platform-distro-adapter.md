# ADR-0004 — Dual platform (Fedora + WSL/Ubuntu) via a distro adapter

**Date:** 2026-07-01 · **Status:** Accepted

## Context

earth moved from Windows 11 + WSL2 to Fedora 44, but the WSL path remains valuable — both
for the open-source audience and for any Windows machine that joins later. Maintaining two
parallel stacks would double the surface; the runtime decision (ADR-0002) already unifies
the service layer across both.

## Decision

Support **both platforms through one code path**: podman + quadlets everywhere, with distro
differences isolated in a **provisioning adapter** (`platform/` in the future package).

| Tier | Platforms | Notes |
|---|---|---|
| **Server (full stack)** | Fedora (primary); Ubuntu — bare-metal or WSL | WSL is a **detection flag inside the debian adapter**, not a separate platform; the same apt path serves future bare-metal Ubuntu nodes. NVIDIA differs per distro: rpmfusion akmods (open kernel modules — required for Blackwell/RTX 5080) vs. apt/ubuntu-drivers. WSL specifics: `nvidia-ctk cdi generate --mode=wsl`, cgroup v2 / `.wslconfig` notes for rootless podman, single distro (the old two-distro dev/services split is retired), Windows-host firewall docs for LAN access. |
| **Client** | macOS, any Linux/WSL | `terrella client` renders client configs (Continue.dev, shell env for tailnet endpoints, virtual keys) and must run on macOS from day one. |
| **Future inference node** | Apple-silicon macOS | The M7 node agent must **not hard-require quadlets/systemd** — the Python package + a serving driver (ollama-with-Metal or MLX) + launchd covers a Mac mini, a legitimate 2026 inference node. Out of scope until M7; the interface keeps the door open. |

Gaming toggle on both server platforms: `terrella stop` (stops `terrella.target`, frees VRAM);
`wsl --shutdown` remains the WSL nuclear option.

## Consequences

- The provisioner is written adapter-first (fedora/dnf lands in M0–M1; debian/apt + WSL
  detection as a compiling stub until tested on hardware).
- Docs describe one stack with per-platform install notes, not two guides.
- CI validates quadlets and the debian adapter even while untested on real WSL hardware.
