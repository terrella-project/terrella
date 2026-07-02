# ADR-0005 — Multi-node-ready interfaces; no A2A protocol

**Date:** 2026-07-01 · **Status:** Accepted

## Context

The homelab will grow beyond earth (more Linux servers/GPUs are planned, and the Mac mini is
a potential Apple-silicon inference node). Designing multi-node too early risks speculative
plumbing; designing single-node-only risks rework. Separately, agent-to-agent protocols
(A2A) are in vogue for cross-vendor agent interop.

## Decision

- **Design interfaces now, build multi-node last (M7).** The config schema, DB schema
  (`nodes`, `node_models`), and driver interfaces carry node-awareness from M2 onward, but
  **zero multi-node code exists before M7**.
- M7 shape: a **node agent** (same Python package, platform-agnostic — systemd/quadlets on
  Linux, launchd on macOS) registers inventory/health/GPU capacity into Postgres on the
  primary; the gateway renders per-node routes with warm-node preference; Prometheus
  federates node exporters.
- **No A2A.** For a single-operator homelab, agent-to-agent protocol adoption is
  speculation: there is no second implementer and no trust boundary between one's own
  agents. MCP (agent→tools), HTTP (service→service), and Postgres (shared state) cover every
  actual interaction. A one-afternoon reassessment is scheduled inside M7; the expected
  answer remains no unless third-party agents must interoperate with the nodes.

## Consequences

- Single-node work is never blocked on distributed-systems design.
- The cluster copilot agent (Prometheus/journald/podman diagnosis → remediation PRs) lands
  in M7, after there is a cluster to copilot.
