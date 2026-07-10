# Cross-Machine Access

When you're not at the desk (working from **jupiter** or Mac mini), you have two options:

1. **Use paid cloud services directly** — Copilot, Claude Code, Anthropic API, Gemini API all work over the public internet. No extra setup. Use this when you don't need ollama and the latency back to earth isn't worth it.
2. **Tailscale back to earth** — reuse local models and the LiteLLM proxy so paid spend doesn't go up just because you stepped away from the desk.

This doc covers option 2.

## What is Tailscale?

A zero-config mesh VPN. After installing it on each device and logging in with the same account, every device gets a stable hostname (e.g. `earth`, `jupiter`, `mac-mini`) on a private network — your "tailnet". From a coffee shop, jupiter can reach `http://earth:11434` as if it were on the home LAN.

> **Naming transition (M0):** the WSL-era node was `earth-ai`. The Fedora install joins as
> **`earth`**; the `earth-ai` node retires once the migration soak completes (#78). Until
> your clients are updated, substitute whichever node name `tailscale status` shows.

## One-time setup

### Step 1 — install on every device

```bash
# earth (Fedora) — part of provision/fedora/bootstrap.sh:
sudo dnf config-manager addrepo --from-repofile=https://pkgs.tailscale.com/stable/fedora/tailscale.repo
sudo dnf install tailscale
sudo systemctl enable --now tailscaled

# jupiter — install on **Windows** first:
# https://tailscale.com/download/windows
# Then also install inside the WSL distro:
curl -fsSL https://tailscale.com/install.sh | sh

# macOS (Mac mini):
brew install --cask tailscale
```

### Step 2 — bring each device online

```bash
sudo tailscale up --ssh
```

The first run prints a login URL. Open it in a browser and approve the device.

### Step 3 — on earth, expose ollama and LiteLLM to the tailnet

Every stack port binds to `127.0.0.1` only (quadlet units); `tailscale serve` is the sole
remote path:

```bash
tailscale serve --bg --tcp 11434 tcp://127.0.0.1:11434   # ollama
tailscale serve --bg --tcp 4000  tcp://127.0.0.1:4000    # LiteLLM
tailscale serve --bg --tcp 3000  tcp://127.0.0.1:3000    # Grafana (optional)
tailscale serve status
```

> `tailscale serve` exposes the port **only** on the tailnet, not on the public internet. No firewall holes are opened.

### Step 4 — confirm hostnames

```bash
tailscale status
```

Note the magic-DNS name advertised for earth. The default is the Linux hostname; if it's not `earth`, substitute the actual name in the next step.

## LAN posture

Nothing terrella-related is reachable from the local network (#10):

- Every containerized service publishes on `127.0.0.1` only — there is nothing to
  firewall away.
- Host ollama binds `0.0.0.0:11434` (containers must reach it via the host-gateway), so
  firewalld must **not** allow 11434 from the LAN. Note Fedora Workstation's default zone
  opens `1025-65535/tcp+udp` — the terrella zone configuration closes that range.
- Access paths are exactly two: the local console, and the tailnet (`tailscale serve` +
  Tailscale SSH).

## Using it from jupiter (Windows laptop, WSL)

Add these to `~/.bashrc` in the WSL distro so they persist:

```bash
# ollama directly:
export OLLAMA_HOST=http://earth:11434

# LiteLLM (preferred — calls show up in Grafana):
export OPENAI_BASE_URL=http://earth:4000
export OPENAI_API_KEY=<my-virtual-key-from-litellm-config.yaml>
```

Then run any tool that respects those env vars — OpenCode, scripts, etc. — and they'll behave the same as on earth.

```bash
# Quick smoke test from jupiter WSL:
curl -s http://earth:11434/api/tags | head
curl -s http://earth:4000/health/liveness
```

> **Jupiter note:** Claude Code and GitHub Copilot use their own auth (subscription-based) and do **not** route through LiteLLM — those calls won't appear in Grafana. Use LiteLLM for scripts and OpenCode.

## Using it from Mac mini

```bash
# Add to ~/.zshrc:
export OLLAMA_HOST=http://earth:11434
export OPENAI_BASE_URL=http://earth:4000
export OPENAI_API_KEY=<my-virtual-key-from-litellm-config.yaml>
```

```bash
# Quick smoke test from Mac mini:
curl -s http://earth:11434/api/tags | head
curl -s http://earth:4000/health/liveness
```

## ACLs

The default Tailscale ACL is "all my devices can reach all my devices" — fine for a personal tailnet. If you ever add a non-personal device (say, a client's machine), tag it and restrict ports 11434/4000 in the Tailscale admin console so only your devices can reach the AI services.

## Tradeoffs

| | Direct paid services | Tailscale → earth |
|---|---|---|
| Latency | low (provider's edge) | one extra hop |
| Cost | ticks the meter | free (uses your hardware) |
| Privacy | data leaves your network | stays on earth |
| Works offline | only with cached responses | no — needs tailnet |

Rule of thumb: if it's a quick local-quality task, prefer Tailscale. If it's a hard problem you'd pay for anyway when at the desk, just hit the cloud directly.
