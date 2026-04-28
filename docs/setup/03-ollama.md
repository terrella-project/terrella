# ollama (Local LLM Engine)

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

The list of models to pull is checked into the repo at [`provision/models.list`](../../provision/models.list). The provisioner reads this file; you can also pull them by hand:

```bash
cd ~/src/jomkz/earth-ai
# Either run the provisioner (idempotent) ...
bash provision/provision.sh
# ... or pull only the model section:
awk '!/^[[:space:]]*(#|$)/ {print $1}' provision/models.list \
  | xargs -n1 ollama pull
```

The default set is roughly **57 GB** on disk — check space first (`df -h ~`). What each model is for, when to add or remove one, and how to update the list: → [reference/local-models.md](../reference/local-models.md).

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

## ✅ Verification

```bash
ollama run qwen2.5-coder:14b "say hi in one word"
```

If you get a response back in a second or two with GPU activity in `nvidia-smi` (in another terminal), the inference path is working end-to-end. → on to [Open WebUI setup](04-open-webui.md).

> Troubleshooting GPU not used / model loaded but slow → see [operations/troubleshooting.md](../operations/troubleshooting.md#gpu-not-utilized).
