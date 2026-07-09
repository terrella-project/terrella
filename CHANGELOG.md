# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions will follow
[SemVer](https://semver.org/) once the `terrella` CLI ships (M1).

Every PR adds an entry under `[Unreleased]` (enforced by CI; the `no-changelog` label
exempts chores — see [docs/project-management.md](docs/project-management.md)).

## [Unreleased]

### Fixed

- **`OPENWEBUI_DB` wired through the env plumbing** (`stack/.env.example`,
  `generate-env.sh`): the compose file interpolates it into Open WebUI's `DATABASE_URL`
  but it only existed in the live `.env` — a fresh `generate-env.sh` run produced a
  malformed URL. Inspection of the rescued data (#5) confirmed the dedicated `openwebui`
  Postgres DB is the live chat store; `LITELLM_EXPORTER_API_KEY` added to `.env.example`
  while at it (#8).

### Added

- **Apache-2.0 LICENSE** and community health files: `CONTRIBUTING.md`, `SECURITY.md`
  (private vulnerability reporting), `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1),
  `.github/CODEOWNERS` (#53; ADR-0009).
- **REUSE/SPDX compliance**: whole-tree `REUSE.toml` + `LICENSES/`, `reuse lint` CI
  workflow (#58 — DCO remains deferred).
- **Supply-chain baseline**: OpenSSF Scorecard workflow + README badge, Dependabot for
  GitHub Actions, all workflow actions pinned to commit SHAs.
- **PyPI name reservation**: stub `terrella` package (`pyproject.toml` +
  `terrella/__init__.py`) and a Trusted Publishing release workflow
  (`.github/workflows/release.yml`); release process documented in
  `docs/operations/release.md` (advances #54).
- Root `.gitignore` (Python build artifacts, env files, generated configs).

- Roadmap (`ROADMAP.md`) with phases M0–M7: Fedora migration → terrella CLI → config/secrets/
  2026 models → observability v2 → agentic ops → benchmark-informed routing → OSS launch →
  multi-node.
- Architecture Decision Records in `docs/adr/` (ADR-0001…0007) covering the tool/platform
  end state, Podman+Quadlets runtime, the LiteLLM driver boundary, dual-platform support,
  multi-node interfaces, the config-in/artifacts-out principle, and the PM framework.
- GitHub-native project management: `docs/project-management.md`, declarative
  `.github/project.yml` + `scripts/project-sync.sh`, issue-form templates, PR template,
  path-based PR labeler, PR-title lint, and this changelog's CI check.
- Runbook for the Project board setup (`docs/runbooks/github-project-setup.md`).

### Changed

- **Project renamed from earth-ai to terrella** after a naming-collision review
  (ADR-0008); repo moved to `terrella-project/terrella`. All brand, CLI, config, and
  path references updated. Live infrastructure names (`Earth-AI` WSL distro, `earth-ai`
  tailnet hostname, the `earth-ai` compose project/volume prefix) deliberately keep
  their names until M0 retires them.
- Personal-deployment docs (machines, subscriptions, manual billing) moved from `docs/`
  to the new `deploy/earth/` overlay (start of the docs de-personalization split, #55).
- Continue.dev sync script output renamed to `terrella-config.yaml`.
- Added `docs/runbooks/rename-migration.md` (per-clone migration checklist).
- Repository transferred from `jomkz/earth-ai` to `mkzsystems/earth-ai`.
- `README.md` / `AGENTS.md` updated for the project's new direction and earth's move to
  Fedora 44.
