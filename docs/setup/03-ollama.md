# Phase 3 — ollama (Local LLM Engine)

ollama is the workhorse: a small server that downloads, manages, and runs LLMs on the GPU. It exposes both its native API and an OpenAI-compatible API on `http://localhost:11434`.

## 3.1 Install ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

The installer creates a systemd service called `ollama` and starts it.

## 3.2 Apply the network and CORS overrides

By default ollama listens only on `127.0.0.1` and rejects browser requests from other origins. We need it to:

- Listen on **all interfaces** (`0.0.0.0`), so other WSL distros, Open WebUI in a container, and Tailscale clients can reach it.
- Allow **all CORS origins** (`*`), so Open WebUI's browser-side JS can call it.

We do this via a systemd drop-in (`override.conf`) so the changes survive ollama upgrades.

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d/
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama
```

> If you want stricter CORS (only allow Open WebUI), set `OLLAMA_ORIGINS="http://localhost:8080"`.

## 3.3 Pull the baseline models

These four cover ~95% of daily work. Pulling all of them is roughly **57 GB**, mostly from the larger qwen variants — make sure you have disk space first (`df -h ~`).

```bash
ollama pull nomic-embed-text       # embeddings for RAG / semantic search
ollama pull qwen2.5-coder:1.5b     # tab-completion sidecar
ollama pull qwen2.5-coder:14b      # daily-driver coder (fits 100% in VRAM)
ollama pull qwen2.5-coder:32b      # best local quality (overflows VRAM)
ollama pull deepseek-r1:14b        # reasoning specialist
ollama pull gemma2:9b              # generalist / summaries / log triage
```

What each one is for, and when to use it: → [reference/local-models.md](../reference/local-models.md).

## 3.4 Verify ollama is healthy

Three checks. All three should pass.

```bash
# 1. systemd thinks it's running
systemctl is-active ollama
# → active

# 2. It's listening on 0.0.0.0:11434
ss -tlnp | grep 11434
# → 0.0.0.0:11434 listening

# 3. The HTTP API answers and returns the models we just pulled
curl -s http://127.0.0.1:11434/api/tags | python3 -m json.tool | head -20
```

## 3.5 Refresh the model snapshot in the repo

[`models.txt`](../../models.txt) is a checked-in snapshot of `ollama list`. Refresh it after every pull/rm:

```bash
cd ~/src/jomkz/earth-ai
ollama list > models.txt
```

## ✅ Verification

```bash
ollama run qwen2.5-coder:14b "say hi in one word"
```

If you get a response back in a second or two with GPU activity in `nvidia-smi` (in another terminal), the inference path is working end-to-end. → on to [Phase 4](04-open-webui.md).

> Troubleshooting GPU not used / model loaded but slow → see [operations/troubleshooting.md](../operations/troubleshooting.md#gpu-not-utilized).
