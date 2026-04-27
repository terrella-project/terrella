# Cross-Machine Access

When you're not at the desk, you have two options:

1. **Use paid cloud services directly** — Copilot, Claude Code, Anthropic API, Gemini API all work over the public internet. No extra setup. Use this when you don't need ollama and the latency back to earth isn't worth it.
2. **Tailscale back to earth** — reuse local models and the LiteLLM proxy so paid spend doesn't go up just because you stepped away from the desk.

This doc covers option 2.

## What is Tailscale?

A zero-config mesh VPN. After installing it on each device and logging in with the same account, every device gets a stable hostname (e.g. `earth-ai`, `laptop`, `mac-mini`) on a private network — your "tailnet". From a coffee shop, your laptop can reach `http://earth-ai:11434` as if it were on the home LAN.

## One-time setup

### Step 1 — install on every device

```bash
# Ubuntu / Earth-AI WSL / laptop (Linux):
curl -fsSL https://tailscale.com/install.sh | sh

# macOS (Mac mini):
brew install --cask tailscale
```

Windows: install from <https://tailscale.com/download/windows>.

### Step 2 — bring each device online

```bash
sudo tailscale up --ssh
```

The first run prints a login URL. Open it in a browser and approve the device.

### Step 3 — on Earth-AI WSL, expose ollama and LiteLLM to the tailnet

```bash
tailscale serve --bg --tcp 11434 tcp://localhost:11434   # ollama
tailscale serve --bg --tcp 4000  tcp://localhost:4000    # LiteLLM
tailscale serve --bg --tcp 3000  tcp://localhost:3000    # Grafana (optional)
tailscale serve status
```

> `tailscale serve` exposes the port **only** on the tailnet, not on the public internet. No firewall holes are opened.

### Step 4 — confirm hostnames

```bash
tailscale status
```

Note the magic-DNS name advertised for the Earth-AI node. The default is the Linux hostname; if it's not `earth-ai`, substitute the actual name in the next step.

## Using it from laptop / Mac mini

```bash
# ollama directly:
export OLLAMA_HOST=http://earth-ai:11434

# LiteLLM (preferred — calls show up in Grafana):
export OPENAI_BASE_URL=http://earth-ai:4000
export OPENAI_API_KEY=<my-virtual-key-from-litellm-config.yaml>
```

Then run any tool that respects those env vars — Aider, OpenCode, scripts, etc. — and they'll behave the same as on earth.

```bash
# Quick smoke test from laptop:
curl -s http://earth-ai:11434/api/tags | head
curl -s http://earth-ai:4000/health/liveness
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
