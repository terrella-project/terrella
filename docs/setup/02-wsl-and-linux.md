# WSL & Linux Base

Now you'll prepare the Linux side: enable systemd, install dependencies, and verify GPU passthrough. Open the **Earth-AI** terminal (or Ubuntu-24.04 if Earth-AI doesn't exist yet — see note below).

> **About the Earth-AI distro:** The recommended layout is to clone the second WSL distro from a fresh `Ubuntu-24.04` install and rename it `Earth-AI` (so it shows up that way in the Start menu). The simplest path: do this on `Ubuntu-24.04` first to confirm it works, then later export/import a clone called `Earth-AI` for the AI services. For a single-distro setup, just stay in `Ubuntu-24.04`.

## 2.1 Enable systemd

WSL doesn't run systemd out of the box, but ollama is shipped as a systemd service. Edit `/etc/wsl.conf`:

```bash
sudo nano /etc/wsl.conf
```

Set the contents to:

```ini
[boot]
systemd=true

[user]
default=john
```

> Replace `john` with your Linux username. The `[user]` section is optional but means new terminals open as your user instead of root. (`provision/provision.sh` writes this file for you and uses `$USER` automatically.)

Apply the change:

```powershell
# In Windows PowerShell:
wsl --shutdown
```

Reopen the WSL terminal. Verify systemd is now PID 1:

```bash
ps -p 1 -o comm=
# Expected output: systemd
```

## 2.2 Update packages and install dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y zstd python3-pip python3-venv curl git
```

What we're installing:

| Package | Why |
|---|---|
| `zstd` | Decompresses some model and Docker layers. |
| `python3-pip`, `python3-venv` | Needed for Aider. |
| `curl` | Downloads the ollama and Docker installers. |
| `git` | Clone this repo and others. |

## 2.3 Verify GPU passthrough

```bash
nvidia-smi
```

You should see your RTX 5080 listed with the driver version. If `nvidia-smi` is missing or returns no devices:

- Re-check [Windows host setup](01-windows-host.md) step 1.1 (driver install).
- Run `wsl --update` from PowerShell.
- Run `wsl --shutdown` and reopen the terminal.

## 2.4 Clone this repo

```bash
mkdir -p ~/src
cd ~/src
git clone <your fork or origin url> terrella
cd terrella
```

> If you already have the repo, skip this step. The rest of the guide assumes the repo is at `~/src/terrella`.

## ✅ Verification

```bash
ps -p 1 -o comm=          # → systemd
nvidia-smi -L | head -1   # → "GPU 0: NVIDIA GeForce RTX 5080 ..."
ls ~/src/terrella   # → README.md, provision/, docs/, stack/, ...
```

All three good? → on to [ollama setup](03-ollama.md).
