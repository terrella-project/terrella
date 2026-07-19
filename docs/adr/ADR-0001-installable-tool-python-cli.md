# ADR-0001 — terrella becomes an installable tool; CLI in Python

**Date:** 2026-07-01 · **Status:** Accepted

## Context

terrella started as a personal AI-workstation blueprint: documentation, bash provisioning,
and a docker-compose stack, built around one machine (earth, Windows 11 + WSL2). With the
move to Fedora and the intent to open-source, staying a fork-and-adapt template would cap the
project's value; the differentiating work (benchmark-informed routing, agentic ops) needs a
real software home.

## Decision

terrella's end state is an **installable open-source tool/platform**: a CLI (working name
`terrella`) that provisions and manages a personal AI stack on any Linux box, config-driven
and machine-agnostic. The reference setup becomes the first deployment, not the product.

The CLI is **Python 3.12+** — `typer` + `pydantic` + `jinja2`, distributed via
`uv tool install terrella` (with a curl-able `install.sh` bootstrap):

- Every non-trivial existing asset is Python (`benchmark-models.py`,
  `provider-models.py`, both Prometheus exporters); a Python CLI refactors them into a
  package, a Go CLI would rewrite them.
- The differentiators (bench analysis, routing evals, MCP server, agents) are data/LLM
  work — Python's home turf; the official MCP Python SDK is the most mature path.
- The only hot path (the gateway) stays a third-party container; nothing we own needs Go's
  throughput at homelab scale.

**Escape hatch:** side effects are limited to file rendering, `systemctl`/`podman`
invocations, and SQL — so a future Go port would replace a thin shell, not a platform.

Intended license at OSS launch (M6): **Apache-2.0** (explicit patent grant; standard for
infra tooling). Final call is an M6 decision.

## Consequences

- The repo gains a Python package, CI, tests, and release engineering (M1+).
- `stack/` and `provision/` become a transition-period reference (see
  [ROADMAP.md](../../ROADMAP.md) transition policy) and are eventually deleted.
- Docs split over time into product docs vs. the reference deployment (M6).
