# Terrella — Documentation

Welcome. This folder is the single source of truth for how the **Terrella** stack is built, configured, and operated.

If you're new, read it in this order:

1. **[Overview](01-overview.md)** — what this project is, what runs where, and the vocabulary you need.
2. **[Setup guide](setup/README.md)** — building the workstation: Fedora is the primary
   path ([runbooks/fedora-provisioning.md](runbooks/fedora-provisioning.md) +
   [stack/quadlet/](../stack/quadlet/)); the numbered WSL guide remains for the supported
   Windows/WSL platform (ADR-0004).
3. **[Reference](reference/README.md)** — the "look it up" docs: machines, models, subscriptions, tools, and the model-routing decision table.
4. **[Operations](operations/README.md)** — day-2 stuff: cross-machine access, backups, maintenance, troubleshooting, monthly billing entry.

## How to use this documentation

| If you want to… | Go to |
|---|---|
| Understand the architecture in 5 minutes | [01-overview.md](01-overview.md) |
| Build the whole thing from scratch | [setup/](setup/) — follow the numbered files in order |
| Remind yourself which model to use for a task | [reference/routing.md](reference/routing.md) |
| See which models are installed and why | [reference/local-models.md](reference/local-models.md) |
| Work from jupiter (or Mac mini) and reach earth's models | [operations/cross-machine-access.md](operations/cross-machine-access.md) |
| Stop the AI stack so you can play a game | [operations/maintenance.md#gaming-toggle](operations/maintenance.md#gaming-toggle) |
| Back up the stack volumes / databases | [operations/maintenance.md#backup--restore-volumes-open-webui-grafana](operations/maintenance.md#backup--restore-volumes-open-webui-grafana) |
| Measure how fast a local model actually runs | [operations/benchmarking.md](operations/benchmarking.md) |
| Log this month's Copilot / Claude bill | [operations/manual-billing.md](../deploy/earth/manual-billing.md) |
| Diagnose "WebUI won't load" / "GPU not used" | [operations/troubleshooting.md](operations/troubleshooting.md) |

## Conventions used here

- **Terrella** is the project (formerly *earth-ai* — see [ADR-0008](adr/ADR-0008-project-name-terrella.md)). Plain **earth** is the workstation (Fedora 44 since the M0 migration). The legacy **Earth-AI** WSL distro and its `earth-ai` Tailscale hostname survive only on the old, unbooted Windows install and retire at [#78](https://github.com/terrella-project/terrella/issues/78).
- Code blocks tagged `bash` run on earth's Fedora shell unless stated otherwise (WSL-era pages may still reference PowerShell on the Windows host).
- A line starting with `# ` inside a code block is a comment, not a command.
- Anything in `< angle brackets >` is a placeholder you replace before running.
