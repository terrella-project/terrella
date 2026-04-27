# Phase 4 — Open WebUI (Chat Interface)

Open WebUI is the browser-based "private ChatGPT" front-end. It connects to ollama for local models and can also be configured with cloud API keys (Anthropic, Gemini, OpenAI) inside its settings UI. It runs as a single Docker container.

## 4.1 Install Docker Engine

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

Log out and back in (or `exec su - $USER`) so the new group membership takes effect, then verify:

```bash
docker --version
docker compose version
```

> If you get `permission denied` on `docker ps`, your shell hasn't picked up the new group yet — start a fresh terminal.

## 4.2 Launch Open WebUI

The compose file is at the repo root, [`docker-compose.yaml`](../../docker-compose.yaml):

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    restart: always
    network_mode: host
    volumes:
      - open-webui:/app/backend/data
    environment:
      - 'OLLAMA_BASE_URL=http://127.0.0.1:11434'

volumes:
  open-webui:
```

Two design choices worth understanding:

- **`network_mode: host`** — the container shares the WSL distro's network stack, so `127.0.0.1` inside the container is the same as `127.0.0.1` on the host. This means it can reach ollama with zero NAT.
- **`OLLAMA_BASE_URL=http://127.0.0.1:11434`** — explicitly points it at the local ollama. Combined with `OLLAMA_HOST=0.0.0.0` from Phase 3, it works on day one.

Bring it up:

```bash
cd ~/src/jomkz/earth-ai
docker compose up -d
```

The first launch pulls the image (~1 GB). After that, restarts are instant.

## 4.3 First-run

Open <http://127.0.0.1:8080> in your Windows browser. You'll be asked to create the **first** admin account — the very first registration always becomes the admin.

In the UI:

1. **Settings → Models**: Open WebUI auto-discovers ollama models via `OLLAMA_BASE_URL`. You should see all the models you pulled in Phase 3.
2. **Settings → Connections**: optionally add cloud providers (paste your Anthropic/Gemini/OpenAI keys). They'll appear in the model picker alongside local ones.

> If you don't want cloud models inside Open WebUI (because you'd rather route them through LiteLLM for accounting), skip step 2. You can also point Open WebUI at LiteLLM as its OpenAI provider (`http://127.0.0.1:4000`) once Phase 6 is up.

## ✅ Verification

```bash
docker compose ps
# → open-webui ... running ...

curl -sI http://127.0.0.1:8080 | head -1
# → HTTP/1.1 200 OK
```

Browser loads at <http://127.0.0.1:8080>, model picker shows your local models, and you can chat with `qwen2.5-coder:14b`. → on to [Phase 5](05-aider.md).
