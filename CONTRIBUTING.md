# Contributing to Terrella

Thanks for your interest! Terrella is a solo-maintainer project in primary development
(pre-M1), so expect fast-moving ground. External contributions are welcome all the same.

## Ground rules

- Be excellent to each other: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Security problems go through [SECURITY.md](SECURITY.md), not public issues.
- Before building anything sizable, open an issue first — the roadmap
  ([ROADMAP.md](ROADMAP.md)) sequences work strictly, and PRs that jump phases will be
  parked.

## How work is organized

The full model lives in [docs/project-management.md](docs/project-management.md); the short
version:

- **Issue types** (Epic/Feature/Task/Spike/Bug) classify work; `component:*` labels route
  it; milestones are the roadmap phases M0–M7.
- Architectural decisions are **ADRs** in [docs/adr/](docs/adr/) — propose one when a
  change alters an interface, dependency, or principle.
- Generic tool docs go in `docs/`; the maintainer's deployment specifics live in
  `deploy/earth/` (see the placement rule in [AGENTS.md](AGENTS.md)).

## Pull requests

1. Fork/branch from `main`. PRs merge by squash, so the **PR title must be a
   [Conventional Commit](https://www.conventionalcommits.org/)** —
   `type(scope): subject`, where scope mirrors a `component:*` label
   (e.g. `feat(gateway): render aliases from terrella.yaml`). CI lints this.
2. **Every PR updates `CHANGELOG.md`** under `[Unreleased]` (CI-enforced; maintainers can
   apply the `no-changelog` label for pure chores).
3. Licensing is [REUSE](https://reuse.software/)-compliant Apache-2.0 (see
   [ADR-0009](docs/adr/ADR-0009-licensing-and-compliance.md)); `REUSE.toml` covers the whole
   tree, so new files need no header unless they carry a different license. CI runs
   `reuse lint`.
4. **DCO sign-off is not currently required** (revisited when regular external
   contributors appear — tracked in issue #58).

## Dev setup

The repo is currently documentation + bash + compose configs; there is no build. Useful
checks before pushing:

```bash
bash -n stack/scripts/*.sh provision/*.sh scripts/*.sh   # shell syntax
uvx reuse lint                                           # licensing metadata
```

The Python package (`terrella/`) is a stub reserving the PyPI name until the M1 CLI
scaffold; don't add code to it ahead of the roadmap.
