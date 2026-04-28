# Windows Host

You're configuring the Windows host that the rest of the stack will run on top of. Everything here is one-time setup performed in **Windows**, not in WSL.

## 1.1 Install / update the NVIDIA driver

You need a recent NVIDIA Game Ready or Studio driver for the RTX 5080. WSL2's GPU passthrough (CUDA) depends on it.

- Download from <https://www.nvidia.com/Download/index.aspx> and install.
- After install, reboot if prompted.

> **Why this matters:** ollama uses CUDA inside WSL to run models on the GPU. If the Windows-side driver is missing or stale, you'll see CPU-only inference (~10× slower) or hard failures.

## 1.2 Install WSL with Ubuntu 24.04

Open **PowerShell as Administrator** and run:

```powershell
wsl --install -d Ubuntu-24.04
```

This installs WSL2 itself (if not already there) and creates a distro called `Ubuntu-24.04`. You'll be prompted for a Linux username and password the first time you launch it.

> We'll add the second distro (`Earth-AI`) later. For now, one is enough.

## 1.3 Configure the WSL hardware envelope (`.wslconfig`)

By default WSL2 will grab as much RAM as it wants. Cap it so games and other Windows apps stay responsive.

1. Press `Win + R`, type `%UserProfile%`, press Enter.
2. Create a file in that folder named `.wslconfig` (no extension) with this content:

```ini
[wsl2]
memory=48GB
processors=16
networkingMode=mirrored
localhostForwarding=true
```

Field by field:

- **`memory=48GB`** — leaves 16 GB for Windows on a 64 GB box. Adjust to taste.
- **`processors=16`** — leaves cores free for Windows. Adjust to your CPU.
- **`networkingMode=mirrored`** — the magic line: WSL shares Windows's `localhost`. This is what lets your dev distro reach `localhost:11434` and hit ollama in the AI distro.
- **`localhostForwarding=true`** — belt-and-braces, ensures Windows browsers can reach Linux ports on `127.0.0.1`.

## 1.4 Apply the changes

```powershell
wsl --shutdown
```

This terminates the WSL VM. Next time you open a WSL terminal, the new `.wslconfig` takes effect.

## 1.5 (Optional) Open the Windows Firewall for LAN access to ollama

If you want **other devices on your home LAN** (not just Tailscale) to reach ollama on this machine, add an inbound TCP rule for port `11434`. Open **PowerShell as Administrator**:

```powershell
New-NetFirewallRule `
  -DisplayName "Ollama LAN" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 11434 `
  -Action Allow
```

> Skip this if you only intend to reach earth from the same machine or via Tailscale (recommended for security).

## ✅ Verification

```powershell
wsl --status
```

You should see `Default Distribution: Ubuntu-24.04` and `Default Version: 2`. If yes, move on to [WSL & Linux base setup](02-wsl-and-linux.md).
