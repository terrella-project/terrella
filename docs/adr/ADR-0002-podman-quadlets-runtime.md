# ADR-0002 — Podman + Quadlets runtime; drop compose & host networking

**Date:** 2026-07-01 · **Status:** Accepted

## Context

The stack ran as a docker-compose project on WSL, with every service on
`network_mode: host` — a workaround for WSL's localhost sharing. earth now runs Fedora 44;
the compose file and its networking assumptions were designed for constraints that no longer
exist, and host networking on a LAN-connected Linux box exposes services the WSL NAT used to
shield.

## Decision

- **Podman + Quadlets** is the target runtime: each service is a systemd unit generated as a
  quadlet, rootless where possible, GPU via CDI (`nvidia-container-toolkit`). Quadlets work
  on both Fedora and Ubuntu-WSL (systemd is already enabled there), so one runtime serves
  both supported platforms.
- **Host networking is dropped**, not ported: services join a named podman network and
  publish only on loopback and the Tailscale interface; firewalld zones are managed
  explicitly.
- An **`terrella.target`** systemd target groups the stack — `systemctl stop terrella.target`
  frees VRAM and replaces the old `wsl --shutdown` gaming toggle.
- Escape hatch: the renderer supports per-service rootful/rootless choice in case rootless
  GPU access fights back (SELinux booleans, CDI edge cases).

## Consequences

- M0 hand-writes the quadlets (they become M1's golden test fixtures); docker-compose is
  retired after M1 reproduces them.
- Every `127.0.0.1` assumption in configs and exporters must be revisited (pasta
  host-gateway semantics for reaching host ollama is the known papercut).
- Backup/restore procedures move from `docker run`/`docker compose exec` to podman-native
  equivalents (`podman unshare` for rootless volume ownership).
