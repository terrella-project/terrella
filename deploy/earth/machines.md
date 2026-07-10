# Machines

Three development machines. earth is the primary; jupiter (laptop) and Mac mini are used away from the desk.

## earth (primary workstation)

- **OS:** Fedora 44 Workstation (kernel 7.0.14-201.fc44), reinstalled July 2026 — the M0
  migration ([epic #3](https://github.com/terrella-project/terrella/issues/3)). The old
  Windows 11 + WSL install remains on its own disk (bootable, mounted read-only for the
  data rescue) until #78 retires it.
- **Hostname:** `earth`
- **Hardware:** MSI MS-7D30
  - CPU: 12th Gen Intel Core i9-12900K — 16 cores / 24 threads
  - RAM: 64 GB
  - GPU: NVIDIA GeForce RTX 5080 (16 GB VRAM, Blackwell — open kernel modules required),
    driver 595.80 via rpmfusion akmod-nvidia; Intel UHD Graphics 770 (iGPU)
  - Networking: Intel Wi-Fi 6E AX211 160MHz (`wlo1`)
- **Stack:** rootless podman quadlets under the login user
  ([stack/quadlet/](../../stack/quadlet/)) — Open WebUI, LiteLLM, Postgres, Prometheus,
  Grafana, exporters, github-mcp on the named `terrella` network, every port on
  `127.0.0.1` only; **ollama** runs on the host as a systemd user service
  (`0.0.0.0:11434`, firewalled from the LAN). `systemctl --user stop
  terrella-inference.target` is the gaming toggle. No WSL, no dev/services distro split —
  the repo is cloned at `~/src/mkzsystems/terrella-project/terrella` and developed
  in place.
- **Role:** all heavy local model work runs here. Always-on. Other machines reach back to earth via Tailscale when away.
- **Installed:** see [tools.md](../../docs/reference/tools.md).

### Verify the stack from earth

```bash
systemctl --user status terrella.target
curl -s http://localhost:11434/api/tags | jq '.models[].name'
curl -s http://127.0.0.1:4000/health/liveness
```

Expected: list of models from [local-models.md](../../docs/reference/local-models.md).

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
# On every machine (earth, jupiter, Mac mini)
# https://tailscale.com/download
tailscale up --ssh
```

**On earth** (so the tailnet sees ollama and LiteLLM — the only remote path; every stack
port binds loopback):

```bash
tailscale serve --bg --tcp 11434 tcp://127.0.0.1:11434
tailscale serve --bg --tcp 4000  tcp://127.0.0.1:4000
tailscale serve status
```

**From jupiter / Mac mini** — point clients at earth's MagicDNS name:

```bash
# ollama
export OLLAMA_HOST=http://earth:11434

# LiteLLM (use the same hostname as earth advertises on tailnet)
export OPENAI_BASE_URL=http://earth:4000
export OPENAI_API_KEY=<my-virtual-key-for-this-machine>
```

(The WSL-era node was `earth-ai`; it retires at #78. Check `tailscale status` for the
live name. On jupiter, add these to your WSL `~/.bashrc` so they persist across sessions.)

### Tailscale ACL note

By default the tailnet is fully open between my own devices. No ACL changes are required for personal use. If a non-personal device is ever added, restrict tags so only my devices can hit ports 11434 / 4000.

---

## Gathering machine specs

Run these on each machine to get accurate version strings for the prerequisites table below.

**Windows (PowerShell) — jupiter host:**
```powershell
# Full hardware summary
systeminfo

# OS / hardware detail
Get-ComputerInfo | Select-Object CsName, CsProcessors, CsNumberOfLogicalProcessors, CsTotalPhysicalMemory, OsName, WindowsVersion | Format-List
```

**Linux — earth (Fedora) or jupiter WSL:**
```bash
echo "=== OS ===" && cat /etc/os-release | head -2
echo "=== Kernel ===" && uname -r
echo "=== CPU ===" && lscpu | grep -E 'Model name|Socket|Thread|Core|CPU\(s\)'
echo "=== RAM ===" && free -h
echo "=== GPU ===" && nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || echo "no GPU"
```

**Prerequisites table one-liner (Linux):**
```bash
printf "podman: "; podman --version 2>/dev/null || echo "not installed"
printf "Tailscale: "; tailscale version 2>/dev/null | head -1 || echo "not installed"
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

| Item | earth (Fedora 44) | jupiter | Mac mini |
|---|---|---|---|
| podman | ✅ 5.8.3 (rootless quadlets) | n/a (not needed) | _TODO_ |
| Tailscale | ⏳ pending (#4 bootstrap apply) | ✅ | _TODO_ |
| ollama | ✅ 0.31.2 (user service, `~/.local`) | n/a (uses earth's) | n/a |
| VS Code | ✅ | ✅ (Remote-WSL) | n/a |
| Claude Code CLI | ✅ | ❌ not installed | _TODO_ |
| OpenCode | _TODO_ | ❌ not installed | _TODO_ |
| gh (GitHub CLI) | ✅ 2.96.0 | ✅ 2.45.0 | _TODO_ |
