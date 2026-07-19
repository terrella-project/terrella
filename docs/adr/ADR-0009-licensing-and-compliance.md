# ADR-0009 — Apache-2.0, REUSE compliance now, DCO deferred

**Date:** 2026-07-01 · **Status:** Accepted

## Context

Until this decision the repo had **no license** — legally all-rights-reserved despite the
open-source intent stated since ADR-0001. ADR-0007 deferred licensing and DCO/REUSE to M6
(OSS launch), but the terrella rename ([ADR-0008](ADR-0008-project-name-terrella.md))
touches every file and moves the repo to a new org — the cheapest possible moment to settle
the legal layer, and the PyPI stub published at the rename needs license metadata anyway.

## Decision

- **Apache-2.0** for the whole repository — code *and* documentation (single-license repo;
  no CC-BY split). Rationale: the 2026 default for infrastructure tooling (Kubernetes,
  Podman, LiteLLM), explicit patent grant, corporate-adoption friendly; a docs/code license
  split adds bookkeeping with no benefit at this scale.
- **REUSE compliance now** (amends ADR-0007's M6 deferral): a whole-tree aggregate
  annotation in `REUSE.toml` + `LICENSES/Apache-2.0.txt`, enforced by `reuse lint` in CI.
  New files need no SPDX header unless they carry a different license.
- **DCO stays deferred** (per ADR-0007): sign-offs add contributor
  friction with no benefit while there are no external contributors. Revisited when they
  appear — tracked in issue #58.
- Supply-chain baseline set at the same time: GitHub Actions pinned to commit SHAs,
  Dependabot on the `github-actions` ecosystem, OpenSSF Scorecard workflow, and PyPI
  **Trusted Publishing** (OIDC; no long-lived tokens) for releases.

## Consequences

- The repo is actually open source; the GitHub license badge and community-standards
  checklist resolve.
- Every future file is automatically licensed via `REUSE.toml`; CI fails if a file escapes
  coverage.
- The M6 OSS-launch epic shrinks again (license/community files done): what remains is
  de-personalized docs content, GitHub Releases automation, and the announcement (#52).
- Contributions are accepted under Apache-2.0 inbound=outbound (stated in
  [CONTRIBUTING.md](../../CONTRIBUTING.md)); if DCO is adopted later it changes contributor
  workflow, hence the explicit deferral record here.
