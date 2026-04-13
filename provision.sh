#!/bin/bash
# Project Earth: Universal AI Provisioning Script

echo "🚀 Starting AI Workstation Provisioning..."

# 1. System Updates & Core Dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y zstd python3-pip python3-venv curl git

# 2. Configure Systemd for WSL
sudo bash -c 'cat <<EOF > /etc/wsl.conf
[boot]
systemd=true
EOF'

# 3. Setup Ollama with Network Overrides (CORS & Host)
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

sudo mkdir -p /etc/systemd/system/ollama.service.d/
sudo bash -c 'cat <<EOF > /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
EOF'

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama

# 4. Install Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo userm_od -aG docker $USER
fi

# 5. Setup Aider Environment
mkdir -p ~/tools/aider
python3 -m venv ~/tools/aider/venv
~/tools/aider/venv/bin/pip install aider-chat

# 6. Pull Baseline Models
ollama pull qwen2.5-coder:32b
ollama pull deepseek-r1:14b

echo "✅ Provisioning Complete. Please restart your terminal!"