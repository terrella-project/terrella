# Project management

How work is planned, tracked, and prioritized in this repository. The model is
**GitHub-native and declarative**, adapted from the framework the sibling projects evolved
([fighters-legacy](https://github.com/fighters-legacy/fighters-legacy/blob/main/docs/project-management.md)
→ [project-viceroy](https://github.com/mkzsystems/project-viceroy/blob/main/docs/project-management.md)
→ [uio](https://github.com/uio-project/uio/blob/main/docs/project-management.md) /
[astrocyte](https://github.com/mkzsystems/astrocyte/blob/main/docs/project-management.md)),
with all of fighters-legacy's "Rev 2" lessons applied from day one. Adoption rationale and
terrella-specific tailoring: [ADR-0007](adr/ADR-0007-github-native-pm-framework.md).

The desired state lives in [`.github/project.yml`](../.github/project.yml) and is reconciled
by [`scripts/project-sync.sh`](../scripts/project-sync.sh) — the same
config-in/artifacts-out principle the product itself follows
([ADR-0006](adr/ADR-0006-config-in-artifacts-out.md)).

## Two axes: Phase × Epic

- **Phase (milestone)** — *when*. One milestone per roadmap phase, **M0–M7** (see
  [ROADMAP.md](../ROADMAP.md)). Every issue gets a milestone at triage, or the `backlog`
  label if unscheduled. There are deliberately **no `phase-*` labels** — our milestones *are*
  the phases.
- **Epic (issue type)** — *which initiative*. One Epic per milestone, decomposed into
  sub-issues via GitHub's native parent/sub-issue linking (the board's Sub-issues-progress
  field rolls up completion automatically). Tailoring: epics are **phase-scoped 1:1 with
  milestones** — never two open Epics from different phases. Cross-phase threads (gateway
  evolution M2→M3→M5, agentic ops M4→M7) are tracked by `component:*` labels and ADRs, not
  long-lived epics.

## Issue types (source of truth)

GitHub **issue types** (org-level on `terrella-project`) — not labels — classify work. Set exactly
one on every issue; there are deliberately **no `type:*` labels**:

| Type | Use for |
|---|---|
| **Epic** | A large, multi-issue initiative tracked via sub-issues |
| **Feature** | A new capability, request, or idea |
| **Task** | A specific, well-scoped piece of work (incl. docs/chore work) |
| **Spike** | A time-boxed investigation producing a decision or follow-on issues, not a feature |
| **Bug** | An unexpected problem or incorrect behavior |

The issue-form templates in [`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/) preset
the type.

## Labels

Declared in [`.github/project.yml`](../.github/project.yml) (single source of truth) in
three families:

- **`component:*`** — the subsystem an issue touches, mirroring conventional-commit scopes
  and the future package layout: `cli`, `provision`, `runtime`, `gateway`, `serving`,
  `observability`, `data`, `routing`, `agents`, `mcp`, `client`, `secrets`, `docs`, `ci`.
  Auto-applied to PRs by path ([`.github/labeler.yml`](../.github/labeler.yml)); applied to
  issues at triage.
- **RFC workflow** — `rfc` + `status: under-discussion|accepted|rejected|implemented`. An
  RFC is a Feature/Task carrying the `rfc` label, reserved for public contracts (chiefly the
  `terrella.yaml` schema) once they freeze post-OSS; ADRs in [docs/adr/](adr/) cover
  everything pre-1.0.
- **Meta** — `epic` (mirror for filtering), `backlog`, `needs-triage`, `needs-info`,
  `needs-decision`, `blocked`, `no-changelog`, `release`, plus kept GitHub defaults (`bug`,
  `documentation`, `good first issue`, `help wanted`). **No priority labels** — the board's
  `Order` field ranks work.

## Milestones

One per phase, `M0 — Fedora migration` through `M7 — Multi-node`, undated (sizes and
sequencing live in [ROADMAP.md](../ROADMAP.md)). Release-versioned milestones may be
introduced at M6 when the CLI ships publicly.

## The board

Org Project **[terrella 1.0](https://github.com/orgs/terrella-project/projects)** holds every open
item; the built-in **auto-add** workflows add new issues/PRs and sub-issues automatically.

| View | Layout | Purpose |
|---|---|---|
| **Roadmap** | Timeline | Scheduling via Start Date / Target Date, grouped by Milestone |
| **Board** | Kanban | Day-to-day flow by Status (`Todo → In Progress → Done`) |
| **Open Items** | Table | Triage and bulk editing across all fields |

Custom fields (declared in `project.yml`, options defined at creation): **Effort**
(`XS S M L XL`), **Order** (number, manual priority), **Start Date**, **Target Date**.
Views and auto-add are UI-only — see the
[project-setup runbook](runbooks/github-project-setup.md).

## Triage checklist

When opening or grooming an issue, set all of:

- [ ] **Type** — Epic / Feature / Task / Spike / Bug
- [ ] **Milestone** — its phase (or the `backlog` label if unscheduled)
- [ ] **`component:*` label(s)** — the subsystem(s) it touches
- [ ] **Parent** — link it under its phase Epic if applicable
- [ ] **Board** — confirm it's on *terrella 1.0* (auto-add covers new issues); Status `Todo`
- [ ] **Effort** — set when the issue enters active planning

## Delivery loop: issue → branch → PR → merge

1. **Branch** off `main`: `<type>/<short-kebab>` (e.g. `feat/quadlet-renderer`,
   `chore/adopt-pm-framework`).
2. **Commit** with [Conventional Commits](https://www.conventionalcommits.org/); the scope
   mirrors the `component:*` label (`feat(gateway): render aliases from terrella.yaml`).
   No DCO sign-off is required (revisited with REUSE/SPDX at M6).
3. **PR** referencing the issue (`Closes #NNN`); the title is conventional-commit form
   (enforced by `pr-title-lint`); the path labeler applies `component:*` automatically.
4. **CHANGELOG** — add an entry under `[Unreleased]` in [CHANGELOG.md](../CHANGELOG.md)
   (enforced; apply the `no-changelog` label to exempt a chore/docs-only PR).
5. **Merge** when CI is green. (Branch protection requiring green CI lands with the full M1
   CI matrix.)

## Decision records vs. RFCs

- **ADRs** ([docs/adr/](adr/), `ADR-NNNN-*.md`) — lightweight, dated records for
  architectural decisions during pre-1.0 development.
- **RFCs** — the label-driven workflow (`rfc` + `status:*`) reserved for public contracts
  after they freeze (post-M6): the `terrella.yaml` schema, CLI command contracts, the node
  registration protocol.

## Agents and automation

From M4 onward, timer-driven agents file issues and open PRs (bench regression reports,
spend reports, catalog-watch PRs). They use a **dedicated least-privilege identity/token**,
never the maintainer PAT — the permission matrix lands with the M4 epic (pattern borrowed
from uio's `ai-governance` model). The `project-sync` CI workflow is the one exception that
needs the maintainer-scoped `PROJECT_ADMIN_TOKEN` (org objects), and it is validate/create
only — see the [runbook](runbooks/github-project-setup.md).
