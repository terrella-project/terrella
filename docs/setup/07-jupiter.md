# Jupiter (Windows Laptop, Client Setup)

Jupiter is the laptop: a Windows 11 machine that serves as a mobile development client. It runs no local AI services — instead it reaches earth's ollama and LiteLLM over Tailscale. This phase documents everything needed to get a productive dev environment on jupiter.

> **Scope:** this doc is for jupiter only. Earth's AI stack must already be running (steps 01–06) before Tailscale access is useful.

## 7.1 Windows host prerequisites

On the Windows side of jupiter (no NVIDIA driver needed — no GPU):

1. **Install WSL with Ubuntu 24.04:**

   ```powershell
   # PowerShell as Administrator:
   wsl --install -d Ubuntu-24.04
   ```

2. **Configure `.wslconfig`** — press `Win + R`, type `%UserProfile%`, create `.wslconfig`:

   ```ini
   [wsl2]
   memory=16GB
   processors=8
   networkingMode=mirrored
   localhostForwarding=true
   ```

   Adjust `memory` and `processors` to about half of jupiter's physical RAM/cores. Apply:

   ```powershell
   wsl --shutdown
   ```

> **Single distro:** jupiter uses only the one `Ubuntu-24.04` distro for development. There is no `Earth-AI` equivalent here — AI services run on earth.

## 7.2 WSL Linux base setup

Open the `Ubuntu-24.04` terminal and run the standard base setup:

```bash
# Update packages
sudo apt-get update && sudo apt-get upgrade -y

# Install essentials
sudo apt-get install -y git curl jq python3 python3-pip python3-venv build-essential

# Install gh (GitHub CLI)
(type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
       | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
       | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && sudo apt update && sudo apt install gh -y

# Authenticate GitHub CLI
gh auth login
```

## 7.3 Clone repos

```bash
mkdir -p ~/src
cd ~/src
# Clone your repos as needed, e.g.:
# gh repo clone <org>/<repo>
```

## 7.4 Install Tailscale (Windows + WSL)

Tailscale needs to run on both the Windows host and inside WSL so that both layers can reach the tailnet.

**On Windows:**
Download and install from <https://tailscale.com/download/windows>, then:
```
Start → Tailscale → Log in
```
Approve the device in the browser.

**Inside WSL (Ubuntu-24.04):**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```
A login URL will be printed — open it and approve.

**Verify both are connected:**
```bash
tailscale status
# Should show earth-ai and this machine in the list
```

## 7.5 Point tools at earth's AI services

Add to `~/.bashrc` in WSL so these persist across sessions:

```bash
# Reach earth's ollama over Tailscale
export OLLAMA_HOST=http://earth-ai:11434

# Reach earth's LiteLLM proxy over Tailscale (preferred — calls show up in Grafana)
export OPENAI_BASE_URL=http://earth-ai:4000
export OPENAI_API_KEY=<my-virtual-key-from-litellm-config.yaml>
```

```bash
source ~/.bashrc
```

Get your LiteLLM virtual key from [`stack/observability/litellm/config.yaml`](../../stack/observability/litellm/config.yaml) on earth.

**Smoke test:**

```bash
curl -s http://earth-ai:11434/api/tags | jq '.models[].name'
curl -s http://earth-ai:4000/health/liveness
```

Both should return without error. If they hang, check that earth's Tailscale node is online (`tailscale status`) and that earth-ai's Tailscale serve is configured (see [cross-machine-access.md](../operations/cross-machine-access.md#step-3)).

## 7.6 Install VS Code + Remote WSL

1. Download VS Code for Windows from <https://code.visualstudio.com>.
2. Install the **Remote - WSL** extension (identifier: `ms-vscode-remote.remote-wsl`).
3. Open WSL from inside VS Code: `Ctrl+Shift+P` → **WSL: Connect to WSL**.
4. Install **GitHub Copilot** and **GitHub Copilot Chat** extensions (these authenticate via GitHub login — they use their own subscription and do **not** route through LiteLLM).

## 7.7 Install Claude Code CLI

Inside WSL:

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

Claude Code authenticates via your Anthropic subscription (claude.ai) — run `claude` and follow the OAuth flow on first launch. It reads `CLAUDE.md` files automatically for workspace context.

## 7.8 Install OpenCode

Inside WSL:

```bash
curl -fsSL https://opencode.ai/install | sh
```

OpenCode is configured via `opencode.json` in each workspace root. It can route to Anthropic, Gemini, OpenAI, and ollama (via `OPENAI_BASE_URL`). When `OPENAI_BASE_URL` points at earth's LiteLLM, calls will appear in Grafana.

## 7.9 Continue.dev (VS Code AI)

Install **Continue** from the VS Code marketplace, then configure it to use earth's LiteLLM as the model gateway.

**Get a virtual API key** from earth's LiteLLM admin UI:
- Open <http://earth:4000/ui> (sign in with `LITELLM_MASTER_KEY` from earth's `stack/.env`)
- Virtual Keys → Create Key (name: `jupiter-continue`)
- Copy the `sk-…` key

**Edit `~/.continue/agents/new-config.yaml`** with the apiBase, apiKey, autocomplete + embed models, and **leave the auto-managed markers in place**:

```yaml
%YAML 1.1
---
name: Earth AI
version: 1.0.0
schema: v1

defaults: &defaults
  provider: openai
  apiBase: http://earth:4000/v1
  apiKey: sk-…

chat_roles: &chat_roles
  roles: [chat, edit, apply]

models:
  # >>> chat-tier models (managed by sync-continue-config.sh) >>>
  # <<< chat-tier models <<<

  - name: qwen2.5-coder:1.5b (autocomplete)
    <<: *defaults
    model: ollama/qwen2.5-coder-1.5b
    roles: [autocomplete]
    autocompleteOptions:
      debounceDelay: 250
      maxPromptTokens: 1024

  - name: nomic-embed
    <<: *defaults
    model: ollama/nomic-embed
    roles: [embed]
```

**Sync the chat-tier list** from LiteLLM. The script lives in the earth-ai repo (clone it once on jupiter) and writes `./new-config.yaml` in your current directory by default:

```bash
cd ~/src/jomkz/earth-ai
LITELLM_KEY=sk-… ./stack/scripts/sync-continue-config.sh
```

That replaces only the lines between the `>>>` and `<<<` markers — your autocomplete and embed entries are preserved. Re-run whenever you add or remove models in earth's `litellm/config.yaml`. Use `--config ~/.continue/agents/new-config.yaml` if you want to write straight to Continue's live config file.

Optional flags:

| Flag | Purpose |
|---|---|
| `--host earth` | LiteLLM hostname (default: `earth`) |
| `--port 4000` | Override port |
| `--dry-run` | Print to stdout instead of writing |

## 7.10 Verification checklist

| Check | Command | Expected |
|---|---|---|
| WSL is Ubuntu 24.04 | `lsb_release -d` | `Ubuntu 24.04` |
| Tailscale connected | `tailscale status` | earth-ai listed, `online` |
| earth ollama reachable | `curl -s http://earth-ai:11434/api/tags \| jq '.models[].name'` | list of model names |
| earth LiteLLM reachable | `curl -s http://earth-ai:4000/health/liveness` | `{"status":"OK"}` |
| gh authenticated | `gh auth status` | logged in |
| Claude Code installed | `claude --version` | version string |
| OpenCode installed | `opencode --version` | version string |

## Notes

- **No Docker needed on jupiter.** The observability stack runs on earth. Jupiter only needs the tools above.
- **Copilot and Claude Code are subscription-based** and do not route through LiteLLM — those calls won't appear in Grafana. Use LiteLLM for scripts, OpenCode, and any tooling where you control the base URL.
- **Model routing from jupiter** follows the same heuristics as earth — see [reference/routing.md](../reference/routing.md). The only difference is that all ollama traffic goes over Tailscale rather than localhost.
- **Tailscale must be running on Windows** (not just in WSL) for the MagicDNS names (`earth-ai`) to resolve from WSL. If `earth-ai` doesn't resolve, open the Windows Tailscale tray icon and confirm it shows "Connected".
