# Releases

How Terrella ships to PyPI. Versioning follows [SemVer](https://semver.org/) from the first CLI
release (M1). The only release so far is the `0.0.1` name-reservation stub
([ADR-0008](../adr/ADR-0008-project-name-terrella.md)); `main` carries a `.devN` version
(`0.1.0.dev0`) until the next release is cut.

## Pipeline

[`release.yml`](../../.github/workflows/release.yml) runs on a published GitHub Release
(or manual dispatch) and:

1. Builds the sdist + wheel with `python -m build` from `pyproject.toml`.
2. Publishes to PyPI via **Trusted Publishing** — OIDC from the `pypi` workflow
   environment; **no API tokens exist anywhere**. The publisher is registered on PyPI for
   `terrella-project/terrella` + workflow `release.yml` + environment `pypi`.
3. PEP 740 attestations are generated automatically by `pypa/gh-action-pypi-publish`.

## Cutting a release (from M1 on)

1. Set `__version__` in `terrella/__init__.py` (the only place the version is written;
   `pyproject.toml` reads it at build time); move the `[Unreleased]`
   CHANGELOG section under the new version heading.
2. Merge via PR (title `chore(release): vX.Y.Z`).
3. Create a GitHub Release with tag `vX.Y.Z` — publishing it triggers the pipeline.

Still manual / deferred to M6 ([#54](https://github.com/terrella-project/terrella/issues/54)):
automated GitHub Release creation, changelog extraction into release notes, signed
release artifacts beyond the PyPI attestations.
