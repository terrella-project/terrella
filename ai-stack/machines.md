# Machines

Three development machines. earth is the primary; laptop and Mac mini are used away from the desk.

## earth (primary workstation)

- **Host OS:** Windows 11
- **Hostname (Linux side):** `earth`
- **WSL distros:**
  - **Earth-AI** — WSL 2, Ubuntu. Hosts **ollama** (port 11434) and will host the **AI observability stack** (LiteLLM + Postgres + Prometheus + Grafana).
  - **Ubuntu-24.04** — WSL 2, Ubuntu 24.04.4 LTS, kernel 6.6.87.2-microsoft-standard. **This is the development workspace** (where TrackPro repos are cloned, where VS Code Remote-WSL connects).
- **WSL networking:** mirrored mode — `localhost` is shared between the Windows host and both WSL distros, so from Ubuntu-24.04 I can reach `http://localhost:11434` and hit ollama running in Earth-AI.
- **Role:** all heavy local model work runs here. Always-on. Other machines reach back to earth via Tailscale when away.
- **Installed (Ubuntu-24.04):** see [tools.md](tools.md).

### Verify ollama is reachable from this WSL

```bash
curl -s http://localhost:11434/api/tags | jq '.models[].name'
```

Expected: list of models from [local-models.md](local-models.md).

## laptop

- **OS:** _TODO — fill in (Windows / macOS / Linux)_
- **Role:** mobile development; light editing, code review, docs, communication.
- **Local models:** none. Falls back to:
  1. Paid services (Copilot / Claude Code / Anthropic / Gemini) directly, OR
  2. Tailscale → ollama and LiteLLM on earth.

## Mac mini

- **OS:** macOS _TODO version_
- **Role:** secondary development; iOS work (`trackpro-ios`) since it needs Xcode.
- **Local models:** could run small ones locally if needed (ollama on macOS supports Metal). For now: same fallback as laptop.

---

## Cross-machine access

When working from laptop or Mac mini, two options:

### Option 1 — paid services only (simplest)

GitHub Copilot, Claude Code, Anthropic API, Gemini API all work over the public internet. No setup needed beyond logging in. **Use this when off-network or when local models aren't worth the latency over Tailscale.**

### Option 2 — Tailscale back to earth

Reuse the local models and the LiteLLM proxy on earth so spend on paid services doesn't increase just because I'm not at my desk.

**One-time setup:**

```bash
# On every machine (earth, Earth-AI WSL, laptop, Mac mini)
# https://tailscale.com/download
tailscale up --ssh
```

**On Earth-AI WSL** (so the tailnet sees ollama and LiteLLM):

```bash
# Optional: expose only on the tailnet, not LAN
tailscale serve --bg --tcp 11434 tcp://localhost:11434
tailscale serve --bg --tcp 4000  tcp://localhost:4000
tailscale serve status
```

**From laptop / Mac mini** — point clients at Earth-AI's MagicDNS name:

```bash
# ollama
export OLLAMA_HOST=http://earth-ai:11434

# LiteLLM (use the same hostname as Earth-AI advertises on tailnet)
export OPENAI_BASE_URL=http://earth-ai:4000
export OPENAI_API_KEY=<my-virtual-key-for-this-machine>
```

(Replace `earth-ai` with whatever Tailscale magic-DNS name the Earth-AI node ends up with — check `tailscale status`.)

### Tailscale ACL note

By default the tailnet is fully open between my own devices. No ACL changes are required for personal use. If a non-personal device is ever added, restrict tags so only my devices can hit ports 11434 / 4000.

---

## Prerequisites status

| Item | earth (Ubuntu-24.04) | earth (Earth-AI) | laptop | Mac mini |
|---|---|---|---|---|
| Docker + Compose v2 | ✅ 29.4.1 / v5.1.3 | _TODO_ | _TODO_ | _TODO_ |
| Tailscale | ❌ not installed | _TODO_ | _TODO_ | _TODO_ |
| ollama | n/a (uses Earth-AI's) | ✅ 11434 reachable | n/a | n/a |
| VS Code + Remote-WSL | ✅ | n/a | _TODO_ | n/a |
