# Earth AI — Documentation

Welcome. This folder is the single source of truth for how the **Earth AI** workstation is built, configured, and operated.

If you're new, read it in this order:

1. **[Overview](01-overview.md)** — what this project is, what runs where, and the vocabulary you need.
2. **[Setup guide](setup/README.md)** — step-by-step build of the workstation from a fresh Windows install.
3. **[Reference](reference/README.md)** — the "look it up" docs: machines, models, subscriptions, tools, and the model-routing decision table.
4. **[Operations](operations/README.md)** — day-2 stuff: cross-machine access, backups, maintenance, troubleshooting, monthly billing entry.

## How to use this documentation

| If you want to… | Go to |
|---|---|
| Understand the architecture in 5 minutes | [01-overview.md](01-overview.md) |
| Build the whole thing from scratch | [setup/](setup/) — follow the numbered files in order |
| Remind yourself which model to use for a task | [reference/routing.md](reference/routing.md) |
| See which models are installed and why | [reference/local-models.md](reference/local-models.md) |
| Work from your laptop and reach earth's models | [operations/cross-machine-access.md](operations/cross-machine-access.md) |
| Stop the AI stack so you can play a game | [operations/maintenance.md#gaming-toggle](operations/maintenance.md#gaming-toggle) |
| Back up Open WebUI chats | [operations/maintenance.md#backup--restore-open-webui](operations/maintenance.md#backup--restore-open-webui) |
| Log this month's Copilot / Claude bill | [operations/manual-billing.md](operations/manual-billing.md) |
| Diagnose "WebUI won't load" / "GPU not used" | [operations/troubleshooting.md](operations/troubleshooting.md) |

## Conventions used here

- **Earth-AI** (with hyphen) refers specifically to the **WSL distro** that hosts ollama and the observability stack. Plain **earth** is the whole workstation.
- Code blocks tagged `bash` run inside a WSL terminal unless the prompt says otherwise (`PowerShell` blocks run on the Windows host).
- A line starting with `# ` inside a code block is a comment, not a command.
- Anything in `< angle brackets >` is a placeholder you replace before running.
