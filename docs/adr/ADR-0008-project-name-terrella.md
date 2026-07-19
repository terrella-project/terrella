# ADR-0008 — Rename the project to terrella; move to the terrella-project org

**Date:** 2026-07-01 · **Status:** Accepted

## Context

The project was named **earth-ai** after the workstation ("earth") it started on. Before the
CLI ships (M1) and the OSS launch (M6), the name was re-examined. Collision research
(July 2026):

- **earth-ai / Earth AI** — collides with **Google Earth AI** (Google's geospatial AI
  platform, launched 2025; permanently owns the search results) and **EARTH AI**
  (YC-backed mineral-exploration company holding `earth-ai.com`). The PyPI name `earthai`
  is squatted by a dormant placeholder.
- **terra-ai** (considered) — worse: two exact-name AI companies (`terraai.com`, a funded
  mineral-exploration AI startup; `terraai.io`, enterprise automation), a Stereolabs
  robotics product ("TERRA AI"), a homophone startup (Tera AI), PyPI `terra-ai` taken,
  plus Terraform / Terra-Luna namespace noise.
- **terrella** — a *terrella* ("little Earth") is the small magnetized model of Earth used
  in historical lab experiments (Gilbert, Birkeland): a bench-scale Earth you run
  experiments on. That is almost literally this project — a homelab-scale AI stack named
  after a PC called earth. Collisions are negligible; **PyPI `terrella` is free** and no
  exact-name GitHub repo or software project exists.

The bare `terrella` GitHub org name is taken by a user; the project moves into a dedicated
org (`terrella-project`).

## Decision

- The project is **terrella** (capitalized **Terrella** in prose). Repo:
  **`terrella-project/terrella`** (new dedicated org).
- Derived names: CLI/package `terrella` (PyPI name reserved at rename time, not M1),
  config `terrella.yaml`, systemd target `terrella.target`, DB views `terrella_*`,
  future package dirs `terrella/…`.
- The org Project board is recreated as **"terrella 1.0"** (Projects v2 boards cannot
  transfer between orgs).
- Full git history is retained: a gitleaks scan of all 61 commits plus a targeted grep for
  key fragments / tailnet details found no leaks (closes the #56 audit).
- **Deliberately not renamed** (live infrastructure, not brand; all retired by the M0
  migration): the `Earth-AI` WSL distro, the `earth-ai` Tailscale MagicDNS node name, the
  `earth` workstation hostname, and the compose project name `name: earth-ai` in
  `stack/docker-compose.yml` — that name prefixes the live named volumes
  (`earth-ai_open-webui`, Postgres/Grafana data); renaming it would orphan running data.
  The M0 quadlet stack adopts terrella naming with a deliberate data migration.

## Consequences

- Old GitHub URLs redirect after the transfer; every clone updates its remote (runbook:
  [rename-migration.md](../runbooks/rename-migration.md)). Issues, labels, and milestones
  transfer automatically; org issue types and the board are recreated in the new org.
- The ROADMAP M1 naming check ("check PyPI availability at scaffold time") is resolved
  early; naming no longer blocks M6.
- Legacy docs keep referring to the `Earth-AI` distro and `earth-ai` tailnet name; the
  terminology note in [docs/README.md](../README.md) explains the distinction.
- Licensing and compliance decisions made at the same identity break are recorded
  separately in [ADR-0009](ADR-0009-licensing-and-compliance.md).
