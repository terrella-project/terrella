# 🌍 Project Earth: AI Workstation Setup Guide

This guide details the reconstruction of the "Earth" AI workstation (RTX 5080, i9-12900K, 64GB RAM) to leverage local LLMs for agentic development, augmenting cloud plans (Gemini/Claude) and preventing quota limits.

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
