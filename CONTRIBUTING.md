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

The `terrella` CLI is a Python package (3.12+) managed with [uv](https://docs.astral.sh/uv/);
`uv.lock` is committed. Alongside it, the legacy `stack/` and `provision/` trees are bash and
compose configs until the CLI replaces them (see the transition policy in
[ROADMAP.md](ROADMAP.md)). Checks before pushing:

```bash
uv sync                                                  # .venv with the package + dev tools
uv run terrella --version                                # the CLI from your checkout
uv run pytest                                            # tests/ (CLI + install.sh)
uv run pytest                                            # + stack/scripts/tests (eval tool)
uv run ruff check && uv run ruff format --check          # every Python file in the repo
shellcheck $(git ls-files '*.sh')                        # every shell script
npx markdownlint-cli2                                    # .markdownlint.jsonc rules
lychee --offline .                                       # repo links + #anchors (lychee.toml)
gitleaks git . && gitleaks dir .                         # secrets: history, then tree
scripts/ci/verify-quadlets.sh                            # quadlets -> units -> systemd verify
uvx reuse lint                                           # licensing metadata
```

CI runs all of these on every PR ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)); the
single `ci` check passes only when every job does. `verify-quadlets.sh` needs podman and
systemd (CI uses a Fedora container); `--self-test` shows it rejects bad units. External links
are checked weekly by [`links.yml`](.github/workflows/links.yml), not on PRs.

The version is written in one place, `terrella/__init__.py`; `pyproject.toml` reads it at
build time.
