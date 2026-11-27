# Machines

The machines in the reference deployment. **earth** is the always-on primary; **jupiter**
(laptop), **mercury** (Mac mini), and **luna** (iPhone) are thin clients used away from the
desk. **neptune** (a dedicated AI rig) is up without its GPUs and serves one small model — see
[neptune](#neptune-second-serving-node).

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
  the repo is cloned at `~/src/terrella` and developed in place.
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

- **Host OS:** Windows 11 Pro (24H2)
- **Hostname:** `jupiter`
- **Hardware:** Lenovo ThinkBook (Intel Core Ultra 7 class)
  - CPU: Intel Core Ultra 7 155U — 7 cores / 14 threads
  - RAM: 32 GB
  - GPU: Intel Graphics (integrated)
- **WSL distro:** single `Ubuntu-24.04` distro (Ubuntu 24.04 LTS) — dev workspace only (no Earth-AI equivalent; no local AI services).
- **Networking:** Wi-Fi; Tailscale installed on the Windows host (Wintun tunnel).
- **Role:** mobile development; light editing, code review, docs, communication. Reaches earth's local models via Tailscale when needed.
- **Local models:** none. Falls back to:
  1. Paid services (Copilot / Claude Code) directly, OR
  2. Tailscale → ollama and LiteLLM on earth (preferred for local-model tasks).
- **Confirmed working (Windows):** VS Code + GitHub Copilot (Remote-WSL), Tailscale.
- **Confirmed working (WSL):** gh (GitHub CLI) 2.45.0.
- **Not yet installed (WSL):** Claude Code CLI, OpenCode.

## mercury (Mac mini)

- **OS:** macOS _TODO version_
- **Hostname:** `mercury`
- **Role:** secondary development; iOS development (needs Xcode).
- **Local models:** could run small ones locally if needed (ollama on macOS supports Metal). For now: same fallback as jupiter.

## luna (iPhone)

- **Device:** iPhone 16 Pro Max
- **Hostname:** `luna`
- **Role:** mobile chat client. Reaches the stack over Tailscale — the Open WebUI PWA
  (add-to-home-screen) for chat, using local models and the cost-ledgered gateway. No local
  models.

## neptune (second serving node)

- **Status:** up since 2026-11-27, **without its GPUs**. The four MI100s are passively cooled
  server cards, and in an open tower case three of them reached 98–105 °C junction at idle
  (2026-08-20). They stay out of the machine until ducted airflow is built, and until then
  neptune serves on its CPU. Multi-node machinery is still M7 by
  [ADR-0005](../../docs/adr/ADR-0005-multi-node-interfaces-no-a2a.md); what exists is the
  static second backend that
  [ADR-0010](../../docs/adr/ADR-0010-neptune-future-primary-node.md) allows before it.
- **OS:** Fedora 44 Server.
- **Hostname:** `neptune`
- **Hardware:** ASRock X399 Professional Gaming
  - CPU: AMD Ryzen Threadripper 2970WX — 24 cores / 48 threads
  - RAM: 64 GB
  - GPU, when installed: 4× AMD Instinct MI100 (32 GB HBM2 each = 128 GB total, gfx908 /
    CDNA 1, ROCm)
  - Storage: 2× 4 TB NVMe (the OS, and a volume for the models)
  - Power supply: 1600 W, ATX 3.1
- **Stack:** ollama 0.32.14 on the host as a system service, from the ROCm release tarballs
  (their bundled ROCm userspace runs gfx908 on the in-tree `amdgpu` driver). The version is
  pinned (ADR-0010) and the default context is set to 8192. It listens for the tailnet only.
  A thermal watchdog stops ollama at 92 °C junction and powers the machine off at 100 °C. Its
  provisioning is not in this repo yet.
- **In the gateway:** one pinned name, `neptune/llama3.2:3b`: a 3B model on the CPU, about
  12 tokens/s. It proves the route from the gateway on earth to a second node. No `local/`
  group points at neptune yet.
- **First GPU baseline (2026-08-19):** `llama3.3:70b` (q4) across two MI100s capped at 200 W
  each, 8k context: 14.5 tokens/s decode and 683 tokens/s prompt processing, junction
  temperatures 56–69 °C. Prompt processing is the number ADR-0010 asks for before neptune is
  trusted with agent work.
- **Intended role:** the always-on inference heart — bulk local-model serving (large models
  that do not fit earth's 16 GB), with earth kept as an opportunistic fast/dev node. Bring-up
  checklist: [neptune-provisioning.md](../../docs/runbooks/neptune-provisioning.md).

---

## Cross-machine access

When working from jupiter, mercury, or luna, two options:

### Option 1 — paid services only (simplest)

GitHub Copilot, Claude Code, Anthropic API, Gemini API all work over the public internet. No setup needed beyond logging in. **Use this when off-network or when local models aren't worth the latency over Tailscale.**

### Option 2 — Tailscale back to earth

Reuse the local models and the LiteLLM proxy on earth so spend on paid services doesn't increase when working away from the desk.

**One-time setup:**

```bash
# On every machine (earth, jupiter, mercury)
# https://tailscale.com/download
tailscale up --ssh
```

**On earth** (so the tailnet sees LiteLLM, whose published port binds loopback):

```bash
tailscale serve --bg --tcp 4000  tcp://127.0.0.1:4000
tailscale serve status
```

ollama needs no serve entry: it listens on `0.0.0.0:11434`, and `tailscale0` is in the
`trusted` firewalld zone, so the tailnet reaches it directly. A serve entry for 11434 takes
the port whenever ollama stops, and ollama then cannot start again (#134).

**From jupiter / mercury** — point clients at earth's MagicDNS name:

```bash
# ollama
export OLLAMA_HOST=http://earth:11434

# LiteLLM (use the same hostname as earth advertises on tailnet)
export OPENAI_BASE_URL=http://earth:4000
export OPENAI_API_KEY=<virtual-key-for-this-machine>
```

(The WSL-era node was `earth-ai`; it retires at #78. Check `tailscale status` for the
live name. On jupiter, add these to your WSL `~/.bashrc` so they persist across sessions.)

### Tailscale ACL note

By default the tailnet is fully open between the deployment's own devices. No ACL changes are required for this single-owner setup. If a non-personal device is ever added, restrict tags so only trusted devices can hit ports 11434 / 4000.

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

**macOS (mercury):**
```bash
echo "=== Hardware ===" && system_profiler SPHardwareDataType SPSoftwareDataType
echo "=== Tailscale ===" && tailscale version 2>/dev/null && tailscale status 2>/dev/null || echo "not installed"
```

---

## Prerequisites status

| Item | earth (Fedora 44) | jupiter | mercury |
|---|---|---|---|
| podman | ✅ 5.8.3 (rootless quadlets) | n/a (not needed) | _TODO_ |
| Tailscale | ✅ active (`serve`: 4000, 3000; ollama :11434 direct) | ✅ | _TODO_ |
| ollama | ✅ 0.31.2 (user service, `~/.local`) | n/a (uses earth's) | n/a |
| VS Code | ✅ | ✅ (Remote-WSL) | n/a |
| Claude Code CLI | ✅ | ❌ not installed | _TODO_ |
| OpenCode | _TODO_ | ❌ not installed | _TODO_ |
| gh (GitHub CLI) | ✅ 2.96.0 | ✅ 2.45.0 | _TODO_ |
