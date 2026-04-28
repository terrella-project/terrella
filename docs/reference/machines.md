# Machines

Three development machines. earth is the primary; jupiter (laptop) and Mac mini are used away from the desk.

## earth (primary workstation)

- **Host OS:** Windows 11 Pro (Build 26200, 24H2), installed 1/3/2025
- **Hostname:** `EARTH`
- **Hardware:** MSI MS-7D30
  - CPU: 12th Gen Intel Core i9-12900K — 16 cores / 24 threads, ~3187 MHz base
  - RAM: 64 GB (65,328 MB)
  - GPU: NVIDIA GeForce RTX 5080 (16 GB VRAM, Windows driver 32.0.15.9571), Intel UHD Graphics 770 (driver 32.0.101.7082)
  - BIOS: AMI 1.10, 12/3/2021
  - Networking: Intel Wi-Fi 6E AX211 160MHz
- **WSL distros:**
  - **Earth-AI** — WSL 2, Ubuntu 24.04.4 LTS, kernel 6.6.87.2-microsoft-standard-WSL2. Hosts **ollama** (port 11434) and will host the **AI observability stack** (LiteLLM + Postgres + Prometheus + Grafana). GPU visible via nvidia-smi: RTX 5080 16303 MiB, Linux driver 595.71.
  - **Ubuntu-24.04** — WSL 2, Ubuntu 24.04.4 LTS, kernel 6.6.87.2-microsoft-standard. **This is the development workspace** (where project repos are cloned, where VS Code Remote-WSL connects).
- **WSL networking:** mirrored mode — `localhost` is shared between the Windows host and both WSL distros, so from Ubuntu-24.04 I can reach `http://localhost:11434` and hit ollama running in Earth-AI.
- **Role:** all heavy local model work runs here. Always-on. Other machines reach back to earth via Tailscale when away.
- **Installed (Ubuntu-24.04):** see [tools.md](tools.md).

### Verify ollama is reachable from this WSL

```bash
curl -s http://localhost:11434/api/tags | jq '.models[].name'
```

Expected: list of models from [local-models.md](local-models.md).

## jupiter (laptop)

- **Host OS:** Windows 11 Pro (Build 26200, 24H2), installed 1/16/2025
- **Hostname:** `jupiter`
- **Hardware:** Lenovo ThinkBook 21MA0037US
  - CPU: Intel Core Ultra 7 155U — 7 cores / 14 threads, ~1700 MHz base
  - RAM: 32,233 MB (32 GB)
  - GPU: Intel Graphics (integrated), 2 GB, driver 32.0.101.8332
  - BIOS: LENOVO R2JET37W(1.14), 8/26/2024
- **WSL distro:** single `Ubuntu-24.04` distro (Ubuntu 24.04.4 LTS, kernel 6.6.87.2-microsoft-standard-WSL2) — dev workspace only (no Earth-AI equivalent; no local AI services).
- **Networking:** Wi-Fi (Intel Wi-Fi 6 AX201 160MHz); Tailscale installed on Windows host (Wintun tunnel, `169.254.83.107`).
- **Role:** mobile development; light editing, code review, docs, communication. Reaches earth's local models via Tailscale when needed.
- **Local models:** none. Falls back to:
  1. Paid services (Copilot / Claude Code) directly, OR
  2. Tailscale → ollama and LiteLLM on earth (preferred for local-model tasks).
- **Confirmed working (Windows):** VS Code + GitHub Copilot (Remote-WSL), Tailscale.
- **Confirmed working (WSL):** gh (GitHub CLI) 2.45.0.
- **Not yet installed (WSL):** Claude Code CLI, OpenCode.

## Mac mini

- **OS:** macOS _TODO version_
- **Role:** secondary development; iOS development (needs Xcode).
- **Local models:** could run small ones locally if needed (ollama on macOS supports Metal). For now: same fallback as jupiter.

---

## Cross-machine access

When working from jupiter or Mac mini, two options:

### Option 1 — paid services only (simplest)

GitHub Copilot, Claude Code, Anthropic API, Gemini API all work over the public internet. No setup needed beyond logging in. **Use this when off-network or when local models aren't worth the latency over Tailscale.**

### Option 2 — Tailscale back to earth

Reuse the local models and the LiteLLM proxy on earth so spend on paid services doesn't increase just because I'm not at my desk.

**One-time setup:**

```bash
# On every machine (earth, Earth-AI WSL, jupiter, Mac mini)
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

**From jupiter / Mac mini** — point clients at Earth-AI's MagicDNS name:

```bash
# ollama
export OLLAMA_HOST=http://earth-ai:11434

# LiteLLM (use the same hostname as Earth-AI advertises on tailnet)
export OPENAI_BASE_URL=http://earth-ai:4000
export OPENAI_API_KEY=<my-virtual-key-for-this-machine>
```

(Replace `earth-ai` with whatever Tailscale magic-DNS name the Earth-AI node ends up with — check `tailscale status`. On jupiter, add these to your WSL `~/.bashrc` so they persist across sessions.)

### Tailscale ACL note

By default the tailnet is fully open between my own devices. No ACL changes are required for personal use. If a non-personal device is ever added, restrict tags so only my devices can hit ports 11434 / 4000.

---

## Gathering machine specs

Run these on each machine to get accurate version strings for the prerequisites table below.

**Windows (PowerShell) — earth host or jupiter host:**
```powershell
# Full hardware summary
systeminfo

# GPU (earth only)
Get-WmiObject Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion

# OS / hardware detail
Get-ComputerInfo | Select-Object CsName, CsProcessors, CsNumberOfLogicalProcessors, CsTotalPhysicalMemory, OsName, WindowsVersion | Format-List
```

**Linux / WSL — Ubuntu-24.04, Earth-AI, or jupiter WSL:**
```bash
echo "=== OS ===" && lsb_release -a
echo "=== Kernel ===" && uname -r
echo "=== CPU ===" && lscpu | grep -E 'Model name|Socket|Thread|Core|CPU\(s\)'
echo "=== RAM ===" && free -h
echo "=== GPU (WSL only) ===" && nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || echo "no GPU"
```

**Prerequisites table one-liner (Linux / WSL):**
```bash
printf "Docker: "; docker version --format '{{.Server.Version}}' 2>/dev/null || echo "not installed"
printf "Compose: "; docker compose version --short 2>/dev/null || echo "not installed"
printf "Tailscale: "; tailscale version 2>/dev/null || echo "not installed"
printf "ollama: "; ollama --version 2>/dev/null || echo "not installed"
printf "gh: "; gh --version 2>/dev/null | head -1 || echo "not installed"
```

**macOS (Mac mini):**
```bash
echo "=== Hardware ===" && system_profiler SPHardwareDataType SPSoftwareDataType
echo "=== Tailscale ===" && tailscale version 2>/dev/null && tailscale status 2>/dev/null || echo "not installed"
```

---

## Prerequisites status

| Item | earth (Ubuntu-24.04) | earth (Earth-AI) | jupiter | Mac mini |
|---|---|---|---|---|
| Docker + Compose v2 | ✅ 29.4.1 / v5.1.3 | ✅ 29.4.1 / v5.1.3 | n/a (not needed) | _TODO_ |
| Tailscale | ❌ not installed | ❌ not installed | ✅ | _TODO_ |
| ollama | n/a (uses Earth-AI's) | ✅ 0.20.6 | n/a (uses earth's) | n/a |
| VS Code + Remote-WSL | ✅ | n/a | ✅ | n/a |
| Claude Code CLI | _TODO_ | n/a | ❌ not installed | _TODO_ |
| OpenCode | _TODO_ | n/a | ❌ not installed | _TODO_ |
| gh (GitHub CLI) | ✅ | ❌ not installed | ✅ 2.45.0 | _TODO_ |
