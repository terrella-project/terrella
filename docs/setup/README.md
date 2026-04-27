# Setup Guide

Build the Earth AI workstation from a fresh Windows 11 install. The phases are numbered — **do them in order**. Each one ends with a verification step; if the verification fails, fix it before moving on.

| Phase | What you do | Time |
|---|---|---|
| [1. Windows host](01-windows-host.md) | NVIDIA drivers, enable WSL, set RAM/CPU limits | ~15 min |
| [2. WSL & Linux base](02-wsl-and-linux.md) | Install Ubuntu under WSL, enable systemd, verify GPU passthrough | ~10 min |
| [3. ollama (local LLM engine)](03-ollama.md) | Install ollama, configure CORS / network, pull models | ~30 min (downloads) |
| [4. Open WebUI (chat UI)](04-open-webui.md) | Install Docker, deploy the chat interface | ~5 min |
| [5. Aider (agentic coding CLI)](05-aider.md) | Python venv + Aider, point it at ollama | ~3 min |
| [6. Observability stack](06-observability-stack.md) | LiteLLM + Postgres + Prometheus + Grafana — the proxy + dashboards | ~10 min |
| [7. Jupiter (laptop client)](07-jupiter.md) | Set up the Windows laptop as a dev client — WSL, Tailscale, VS Code, Claude Code, OpenCode | ~20 min |

## The fast path: `provision.sh`

Phases 2–5 are automated by [`provision/provision.sh`](../../provision/provision.sh). It is **idempotent** — safe to re-run. Use the manual instructions in this folder when:

- You want to understand what the script is doing, or
- Something failed and you need to redo just one step, or
- You're adapting the script for a different machine.

```bash
# Inside the Earth-AI WSL terminal, after Phase 1 is done:
cd ~/src/jomkz/earth-ai
bash provision/provision.sh
```

The list of ollama models the script pulls lives in [`provision/models.list`](../../provision/models.list) — edit that file to change the baseline. See [reference/local-models.md](../reference/local-models.md#baseline-set-pulled-by-provisionsh) for what each model is for.

After it finishes:

```powershell
# In Windows PowerShell:
wsl --shutdown
```

Then reopen the Earth-AI terminal and continue with [Phase 6](06-observability-stack.md), which is **not** in `provision.sh` because it has secrets to load.

## Two WSL distros — why?

We use **two** WSL distros on purpose:

- **`Ubuntu-24.04`** is the *development* distro — VS Code Remote-WSL connects here, repositories are cloned here, you live here day-to-day.
- **`Earth-AI`** is the *services* distro — ollama, Docker, Open WebUI, the observability stack run here. You rarely open this terminal except to administer.

This separation means a misbehaving dev tool can't crash the AI services and vice-versa. Both distros share `localhost` thanks to mirrored networking, so from `Ubuntu-24.04` you can hit `http://localhost:11434` and reach ollama running in `Earth-AI`.

The setup phases below all happen **inside the Earth-AI distro**, unless explicitly noted otherwise.

## Once setup is complete

→ Read [reference/routing.md](../reference/routing.md) to learn which model to pick for which task.
→ Read [operations/cross-machine-access.md](../operations/cross-machine-access.md) if you also want to use earth's models from jupiter or Mac mini.
