# 🌍 Project Earth: Universal AI Workstation

This guide details the reconstruction of the "Earth" AI workstation (RTX 5080, i9-12900K, 64GB RAM) to leverage local LLMs for agentic development, augmenting cloud plans (Gemini/Claude) and preventing quota limits. It is designed to be fully automated, reproducible, and optimized for speed.

---

## Phase 1: The Windows Foundation
Before installing Linux, set the hardware boundaries.

1.  **Install NVIDIA Drivers:** Ensure the latest NVIDIA Game Ready or Studio drivers are installed on Windows 11.
2.  **Enable WSL:** Open PowerShell as Admin and run:
    ```powershell
    wsl --install -d Ubuntu-24.04
    ```
3.  **Configure Hardware Allocation (`.wslconfig`):**
    Press `Win + R`, type `%UserProfile%`, and create a file named `.wslconfig`. Paste the following:
    ```ini
    [wsl2]
    memory=48GB
    processors=16
    networkingMode=mirrored
    localhostForwarding=true
    ```
4.  **Restart Windows:** Essential for the `.wslconfig` changes to take effect.

---

## Phase 2: Linux Engine Room (WSL2)
Open the **Earth-AI** (Ubuntu) terminal.

1.  **Enable systemd:**
    Edit the WSL configuration:
    ```bash
    sudo nano /etc/wsl.conf
    ```
    Add these lines:
    ```ini
    [boot]
    systemd=true
    ```
2.  **Apply systemd Changes:** In PowerShell, run `wsl --shutdown`, then restart your terminal.
3.  **Update & Install Dependencies:**
    ```bash
    sudo apt update && sudo apt upgrade -y
    sudo apt install zstd python3-pip python3-venv -y
    ```
4.  **Verify GPU Passthrough:**
    ```bash
    nvidia-smi
    ```
    Confirm the RTX 5080 is detected.

---

## Phase 3: The Local AI Engine (Ollama)
Ollama handles the local inference for your "Quota-Saver" models.

1.  **Install Ollama:**
    ```bash
    curl -fsSL https://ollama.com/install.sh | sh
    ```
2.  **Pull the Model Suite:**
    ```bash
    ollama pull qwen2.5-coder:32b   # Primary Coding Workhorse (fits 16GB VRAM)
    ollama pull deepseek-r1:14b     # Reasoning and Logic specialist
    ollama pull gemma2:9b           # Fast, low-latency tasks
    ```
3.  **Service Management:**
    ```bash
    sudo systemctl enable ollama
    sudo systemctl start ollama
    ```

---

## Phase 4: Mission Control (Open WebUI)
The central hub for local models and cloud API integration.

1.  **Install Docker Engine:**
    ```bash
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    # Restart terminal to apply group changes
    ```
2.  **Deploy Open WebUI:**
    Create a directory: `mkdir ~/earth-ai && cd ~/earth-ai`
    Create `docker-compose.yaml`:
    ```yaml
    services:
      open-webui:
        image: ghcr.io/open-webui/open-webui:main
        container_name: open-webui
        restart: always
        ports:
          - "3000:8080"
        environment:
          - 'OLLAMA_BASE_URL=http://127.0.0.1:11434'
        extra_hosts:
          - "host.docker.internal:host-gateway"
    ```
3.  **Launch:**
    ```bash
    docker compose up -d
    ```
4.  **Access:** Open `http://127.0.0.1:3000` in your Windows browser.

---

## Phase 5: Agentic Tier (Aider)
Direct code manipulation tool for autonomous development.

1.  **Installation:**
    ```bash
    mkdir -p ~/tools/aider && cd ~/tools/aider
    python3 -m venv venv
    source venv/bin/activate
    pip install aider-chat
    ```
2.  **Running Local-First:**
    ```bash
    export OLLAMA_API_BASE=http://localhost:11434
    aider --model ollama/qwen2.5-coder:32b
    ```

---

## 🛡️ Quota Protection Strategy (Daily Workflow)

| Task Type | Recommended Model | Location | Quota Usage |
| :--- | :--- | :--- | :--- |
| **Boilerplate / Syntax** | Qwen 2.5 Coder 32B | Local (5080) | 0% |
| **Logic Riddles / Math** | DeepSeek R1 14B | Local (5080) | 0% |
| **Summaries / Emails** | Gemma 2 9B | Local (5080) | 0% |
| **Architecture Design** | Claude 3.5 Sonnet | Cloud (Paid) | 1 Request |
| **Final Review/Refactor**| Gemini 1.5 Pro | Cloud (Paid) | 1 Request |

**Tip:** Always draft locally in Aider or Open WebUI first. Only send high-confidence, condensed prompts to Claude/Gemini for final polish.

---

## Configuration & Automation Guide

### 1. The Host Bridge (`.wslconfig`)
**Location:** `C:\Users\<YourUser>\.wslconfig`
This file configures the hardware handshake. The `mirrored` networking ensures Windows and Linux share the same IP for zero-latency communication.

```ini
[wsl2]
memory=48GB
processors=16
networkingMode=mirrored
localhostForwarding=true
```

---

### 2. The Universal Provisioner (`provision.sh`)
**Location:** `~/provision.sh`
This script automates the installation and applies the **CORS and Networking fixes** required for the 5080 to talk to Docker.

```bash
#!/bin/bash
# Project Earth: Universal AI Provisioner

# 1. Core Dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y zstd python3-pip python3-venv curl git

# 2. Systemd Activation
sudo bash -c 'cat <<EOF > /etc/wsl.conf
[boot]
systemd=true
EOF'

# 3. Setup Ollama + Network Handshake Fix
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Apply CORS and Network Listen overrides for 5080 detection
sudo mkdir -p /etc/systemd/system/ollama.service.d/
sudo bash -c 'cat <<EOF > /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
Environment="LD_LIBRARY_PATH=/usr/lib/wsl/lib"
EOF'

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama

# 4. Install Docker & Set Permissions
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

# 5. Aider Setup
mkdir -p ~/tools/aider
python3 -m venv ~/tools/aider/venv
~/tools/aider/venv/bin/pip install aider-chat

echo "✅ Provisioning Complete. Run 'wsl --shutdown' in PowerShell and restart."
```

---

### 3. Mission Control (`docker-compose.yaml`)
**Location:** `~/earth-ai/docker-compose.yaml`
Note the `0.0.0.0` binding, which ensures the WebUI is always reachable in mirrored networking mode.

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    restart: always
    ports:
      - "0.0.0.0:3000:8080"
    environment:
      - 'OLLAMA_BASE_URL=http://host.docker.internal:11434'
      - 'WEBUI_SECRET_KEY=earth_secret_123'
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  open-webui:
```

---

### 4. 🚀 Performance Strategy: The "14B Sweet Spot"
To maximize the **RTX 5080 (16GB)**, follow these rules:

* **The Gold Standard:** Use **Qwen 2.5 Coder 14B** or **DeepSeek-R1 14B**. These fit 100% inside VRAM, giving you instant (50+ tokens/sec) responses.
* **The Heavyweight:** Use **Qwen 32B** only when you need deep logic. Note that it will overflow into System RAM, slowing generation to 3-5 words per second.
* **The Quota Defense:** Run Aider (`~/tools/aider/venv/bin/aider`) with the 14B model for 90% of coding tasks. Only use Claude/Gemini in the WebUI for final architectural reviews.

---

### 5. 🔧 Troubleshooting
* **Permission Denied (Docker):** Run `newgrp docker` or restart WSL.
* **WebUI Unreachable:** Access via `http://127.0.0.1:3000` or the Windows IP address. Ensure no Windows apps are using Port 3000.
* **GPU Not Utilized:** Run `sudo systemctl restart ollama`. If `nvidia-smi` shows 0% utilization but high VRAM usage (12GB+), the model is loaded but idle. Generation speed is the true test.

## Maintenance

### Gaming Toggle (Start/Stop WSL)

WSL2 is "on-demand." Open the terminal, it starts. But it does not stop just because the window is closed. Because Ollama reserves VRAM (to keep models fast), it will "steal" frames from games if left running.

#### To Kill Everything (Gaming Mode):
Open Windows PowerShell (as Admin or regular) and run:

```powershell
wsl --shutdown
```

This is the "Nuclear Option." It terminates the entire WSL virtual machine, stops Docker, stops Ollama, and flushes every gigabyte of VRAM back to the GPU.

#### To Start Everything (AI Mode):
Open the `Earth-AI (WSL)` terminal. Because systemd is configured to `restart: always` in the Docker Compose, everything (Ollama + WebUI) will automatically start breathing the moment the terminal opens.

#### 💡 Pro Tip: Create a Desktop Shortcut

    Right-click Desktop > New > Shortcut.

    For the location, enter: wsl.exe --shutdown

    Name it "Terminate Earth AI" or similar.

    Double-click this before launching a heavy game to ensure the 5080 is 100% focused on graphics.

### Backup/Restore of Open WebUI Database

The data (chats, settings, and users) lives in a Docker volume called `open-webui`. Since it's a "named volume," it's tucked away in a protected part of the Linux filesystem.

#### Backup

Run this in the `Earth-AI (WSL)` terminal. It creates a compressed .tar.gz of the entire database.

```bash
docker run --rm -v open-webui:/data -v $(pwd):/backup alpine tar czf /backup/openwebui_backup_$(date +%Y%m%d).tar.gz /data
```

What this does:

1. Grabs the open-webui volume.
2. Compresses it into a single file named with the current date (e.g., `openwebui_backup_20260413.tar.gz`).
3. Drops that file into the current directory.

#### Restore

Just run the reverse.

```bash
docker run --rm -v open-webui:/data -v $(pwd):/backup alpine sh -c "rm -rf /data/* && tar xzf /backup/YOUR_BACKUP_FILE.tar.gz -C /"
```
