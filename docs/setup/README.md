# Setup Guide

> **Fedora is the primary platform since M0** (ADR-0002/ADR-0004). To build the stack on
> Fedora: run [`provision/fedora/bootstrap.sh`](../../provision/fedora/bootstrap.sh)
> (see [runbooks/fedora-provisioning.md](../runbooks/fedora-provisioning.md)), then
> deploy the quadlet stack per [`stack/quadlet/README.md`](../../stack/quadlet/README.md).
> The numbered guide below is the **legacy Windows/WSL path** — still supported (WSL is a
> detection flag in the future debian adapter, ADR-0004), but no new features land here.

Build the Terrella workstation from a fresh Windows 11 install. Follow the steps in order — each ends with a verification step; fix failures before continuing.

| Step | What you do | Time |
|---|---|---|
| [01 — Windows host](01-windows-host.md) | NVIDIA drivers, enable WSL, set RAM/CPU limits | ~15 min |
| [02 — WSL & Linux base](02-wsl-and-linux.md) | Install Ubuntu under WSL, enable systemd, verify GPU passthrough | ~10 min |
| [03 — ollama](03-ollama.md) | Install ollama, configure CORS / network, pull models | ~30 min (downloads) |
| [04 — Open WebUI](04-open-webui.md) | Install Docker, deploy the chat interface | ~5 min |
| [05 — Aider](05-aider.md) | Python venv + Aider, point it at ollama | ~3 min |
| [06 — Full stack](06-observability-stack.md) | LiteLLM + Postgres + Prometheus + Grafana — the proxy + dashboards | ~10 min |
| [07 — Jupiter](07-jupiter.md) | Set up the Windows laptop as a dev client — WSL, Tailscale, VS Code, Claude Code, OpenCode | ~20 min |

## The fast path: `provision.sh` + `sync-models.sh`

Steps 02–05 are automated by two scripts in [`provision/`](../../provision/). Both are **idempotent** — safe to re-run. Use the manual instructions in this folder when:

- You want to understand what the scripts are doing, or
- Something failed and you need to redo just one step, or
- You're adapting them for a different machine.

```bash
# Inside the Earth-AI WSL terminal, after step 01 is done:
cd ~/src/mkzsystems/terrella-project/terrella
bash provision/provision.sh    # machine setup: apt, systemd, ollama, Docker, Aider
bash provision/sync-models.sh  # pull the models listed in provision/models.list
```

The model catalog lives in [`provision/models.list`](../../provision/models.list) — edit that file to add or remove models, then re-run `sync-models.sh`. See [reference/local-models.md](../reference/local-models.md) for what each model is for.

After `provision.sh` finishes:

```powershell
# In Windows PowerShell:
wsl --shutdown
```

Then reopen the Earth-AI terminal (you can run `sync-models.sh` before or after the shutdown), and continue with [step 06 — full stack](06-observability-stack.md), which is **not** in `provision.sh` because it has secrets to load.

## Two WSL distros — why?

We use **two** WSL distros on purpose:

- **`Ubuntu-24.04`** is the *development* distro — VS Code Remote-WSL connects here, repositories are cloned here, you live here day-to-day.
- **`Earth-AI`** is the *services* distro — ollama, Docker, Open WebUI, the observability stack run here. You rarely open this terminal except to administer.

This separation means a misbehaving dev tool can't crash the AI services and vice-versa. Both distros share `localhost` thanks to mirrored networking, so from `Ubuntu-24.04` you can hit `http://localhost:11434` and reach ollama running in `Earth-AI`.

All setup steps below run **inside the Earth-AI distro**, unless explicitly noted otherwise.

## Once setup is complete

→ Read [reference/routing.md](../reference/routing.md) to learn which model to pick for which task.
→ Read [operations/cross-machine-access.md](../operations/cross-machine-access.md) if you also want to use earth's models from jupiter or Mac mini.
