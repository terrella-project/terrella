# Security Policy

## Supported versions

Terrella is pre-release (no versioned releases yet; the CLI ships at M1). Security fixes
land on `main` only.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Use GitHub's private vulnerability reporting:
**[Report a vulnerability](https://github.com/terrella-project/terrella/security/advisories/new)**
(Security tab → "Report a vulnerability").

Include what you found, where (file/service/config), and reproduction steps if you have
them. You can expect an acknowledgement within a week; this is a solo-maintainer project,
so fixes are best-effort but security reports jump the queue.

## Scope notes

- The compose/quadlet stacks bind service ports to `127.0.0.1` by design; cross-machine
  access is via Tailscale. Reports that assume services are exposed to the open internet
  are out of scope unless the default config actually exposes them.
- Secrets are expected to live in `stack/.env` (git-ignored) or podman secrets — a report
  that a *documented placeholder* is "leaked" is out of scope; a real key in git history
  is very much in scope.
