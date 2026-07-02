# Architecture Decision Records

Dated, lightweight records of architectural decisions — the pre-1.0 alternative to a formal
RFC process (mirrors the approach in the sibling astrocyte / viceroy / uio projects). A full
RFC workflow (the `rfc` + `status:*` labels) is reserved for public contracts — chiefly the
`earthai.yaml` schema — once they freeze after the OSS launch (M6).

Format: `ADR-NNNN-short-kebab-title.md` with **Status / Context / Decision / Consequences**.
Statuses: `Accepted`, `Superseded by ADR-XXXX`, `Deprecated`.

| ADR | Title | Status |
|---|---|---|
| [ADR-0001](ADR-0001-installable-tool-python-cli.md) | earth-ai becomes an installable tool; CLI in Python | Accepted |
| [ADR-0002](ADR-0002-podman-quadlets-runtime.md) | Podman + Quadlets runtime; drop compose & host networking | Accepted |
| [ADR-0003](ADR-0003-gateway-litellm-behind-driver-boundary.md) | Keep LiteLLM behind a gateway-driver boundary | Accepted |
| [ADR-0004](ADR-0004-dual-platform-distro-adapter.md) | Dual platform (Fedora + WSL/Ubuntu) via a distro adapter | Accepted |
| [ADR-0005](ADR-0005-multi-node-interfaces-no-a2a.md) | Multi-node-ready interfaces; no A2A protocol | Accepted |
| [ADR-0006](ADR-0006-config-in-artifacts-out.md) | One validated config in, everything generated out | Accepted |
| [ADR-0007](ADR-0007-github-native-pm-framework.md) | Adopt the GitHub-native PM framework | Accepted |
