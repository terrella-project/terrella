# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions will follow
[SemVer](https://semver.org/) once the `terrella` CLI ships (M1).

Every PR adds an entry under `[Unreleased]` (enforced by CI; the `no-changelog` label
exempts chores — see [docs/project-management.md](docs/project-management.md)).

## [Unreleased]

### Added

- **firewalld zone script** (`provision/fedora/firewall.sh`, #10): creates the
  `terrella-lan` zone — Fedora Workstation's service set **without** its default
  `1025-65535/tcp+udp` open range (which would expose host ollama to the LAN) — binds the
  LAN interface to it, and puts `tailscale0` in `trusted`. Loopback + tailnet are the only
  access paths; verification checklist included.
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
