#!/usr/bin/env bash
# Project Earth — Universal AI Workstation provisioner.
#
# Idempotent. Run inside the Earth-AI WSL distro after Phase 1 (Windows /
# WSL install) is done. See docs/setup/ for the full guide.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_FILE="${MODELS_FILE:-${SCRIPT_DIR}/models.list}"

echo "🚀 Starting AI Workstation Provisioning..."

# 1. System updates and core dependencies
echo "▶ apt update / install"
sudo apt update && sudo apt upgrade -y
sudo apt install -y zstd python3-pip python3-venv curl git

# 2. Configure systemd for WSL
echo "▶ /etc/wsl.conf"
sudo tee /etc/wsl.conf > /dev/null <<EOF
[boot]
systemd=true

[user]
default=${USER}
EOF

# 3. Install ollama and apply network / CORS overrides
echo "▶ ollama"
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

sudo mkdir -p /etc/systemd/system/ollama.service.d/
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama

# 4. Install Docker Engine + add user to docker group
echo "▶ docker"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
fi
sudo usermod -aG docker "$USER"

# 5. Aider in a venv at ~/tools/aider
echo "▶ aider"
mkdir -p "$HOME/tools/aider"
if [[ ! -x "$HOME/tools/aider/venv/bin/aider" ]]; then
    python3 -m venv "$HOME/tools/aider/venv"
fi
"$HOME/tools/aider/venv/bin/pip" install --upgrade pip
"$HOME/tools/aider/venv/bin/pip" install --upgrade aider-chat

# 6. Pull baseline ollama models from models.list
echo "▶ ollama models (from ${MODELS_FILE})"
if [[ ! -f "$MODELS_FILE" ]]; then
    echo "  ⚠️  ${MODELS_FILE} not found — skipping model pulls"
else
    # Strip comments and blank lines, take first whitespace-separated field.
    while IFS= read -r model; do
        [[ -z "$model" ]] && continue
        echo "  pulling ${model}..."
        ollama pull "$model"
    done < <(sed -E 's/#.*$//; s/[[:space:]]+$//; /^[[:space:]]*$/d' "$MODELS_FILE" \
              | awk '{print $1}')
fi

echo "✅ Provisioning complete. Run 'wsl --shutdown' in PowerShell, then reopen the terminal."
