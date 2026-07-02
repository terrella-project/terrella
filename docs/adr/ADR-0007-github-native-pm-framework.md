# ADR-0007 — Adopt the GitHub-native PM framework

**Date:** 2026-07-01 · **Status:** Accepted

## Context

Until now the repo had no project-management structure: no roadmap file, default labels, no
milestones, one open issue. The roadmap (M0–M7, see [ROADMAP.md](../../ROADMAP.md)) needs a
tracking system. Three sibling projects (fighters-legacy → project-viceroy → uio/astrocyte)
evolved a proven GitHub-native model, including documented "Rev 2" lessons.

## Decision

Adopt the lineage's framework, tailored to earth-ai (full model:
[docs/project-management.md](../project-management.md)):

- **Repo transferred to the `mkzsystems` org** to gain org issue types
  (Epic/Feature/Task/Spike/Bug) and sit alongside its siblings.
- **Issue types classify work** (no `type:*` labels, viceroy-style); `component:*` labels
  route it; milestones = phases M0–M7.
- **Epics are phase-scoped 1:1 with milestones** (tailoring: a solo maintainer with strictly
  sequential phases needs the WIP guardrail more than cross-phase initiative threading;
  cross-phase threads ride on `component:*` labels + ADRs).
- **No `phase-*` labels** (tailoring: our milestones *are* the phases).
- **PM-as-code**: `.github/project.yml` reconciled non-destructively by
  `scripts/project-sync.sh` (adapted from astrocyte) — the same config-in/artifacts-out
  principle as ADR-0006.
- Rev-2 lessons applied on day one: types enabled before filing issues; Effort options
  (XS–XL) defined at board creation; auto-add enabled at creation; labeler seeded before
  the first PR; the board `Order` field replaces priority labels.
- Delivery loop: conventional commits with component scopes, PR-title lint, enforced
  CHANGELOG (`no-changelog` escape), PR-only flow. **No DCO** (viceroy precedent; DCO +
  REUSE/SPDX are revisited at M6).

## Consequences

- The M6 OSS-launch epic shrinks: templates, labels, changelog discipline, and conventions
  already exist.
- Org-level writes (issue types, Projects) need the maintainer `PROJECT_ADMIN_TOKEN` for CI
  sync; agents that file issues/PRs (M4) get their own least-privilege identity instead.
- Local clones and docs referencing `jomkz/earth-ai` update to `mkzsystems/earth-ai`
  (GitHub redirects the old URL).
