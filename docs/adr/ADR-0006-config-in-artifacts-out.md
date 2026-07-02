# ADR-0006 — One validated config in, everything generated out

**Date:** 2026-07-01 · **Status:** Accepted

## Context

The current stack mixes hand-edited and machine-managed content in the same files — most
sharply in `stack/observability/litellm/config.yaml`, where `update-litellm-config.sh`
splices generated provider-catalog blocks between `>>> ... <<<` markers inside a hand-edited
YAML. Half-generated files are the most fragile pattern in the repo: edits race the
generator, diffs are noisy, and correctness depends on marker discipline.

## Decision

User intent lives in **one validated config file** (`earthai.yaml`, pydantic-validated, JSON
Schema exported). Every runtime artifact is a **100% rendered build output that no human
edits**: quadlets, gateway config, `prometheus.yml`, Grafana provisioning, systemd
targets/timers, client configs, and (from M5) the routing table. `earthai apply --diff` is
the terraform-plan analogue; provider-catalog syncs become *inputs to the renderer*, not
in-place file mutations.

The same principle governs project management: `.github/project.yml` declares labels,
milestones, and board fields, reconciled by `scripts/project-sync.sh` (ADR-0007).

## Consequences

- The marker-block pattern in `update-litellm-config.sh` is retired in M2.
- Rendered artifacts can be regenerated from scratch on any machine — reproducibility
  stops depending on accumulated hand edits.
- Config schema changes become the project's public contract (future RFC territory).
