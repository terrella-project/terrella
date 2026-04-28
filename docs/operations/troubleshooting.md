# Troubleshooting

Symptoms first, then likely causes and fixes.

## "permission denied" running `docker` after fresh install

**Cause:** your user isn't in the `docker` group yet, or the current shell hasn't picked up the new group membership.

```bash
# Confirm membership:
id -nG | tr ' ' '\n' | grep docker

# If missing:
sudo usermod -aG docker "$USER"

# Then either log out / back in, or:
newgrp docker
```

## Open WebUI won't load in the browser

Try, in order:

1. **Is the container up?**
   ```bash
   cd ~/src/jomkz/earth-ai/stack
   docker compose ps
   ```
   If `open-webui` is not "running", `docker compose up -d` and check `docker compose logs open-webui --tail=100`.

2. **Is port 8080 listening?**
   ```bash
   ss -tlnp | grep 8080
   ```
   Expected: a `0.0.0.0:8080` or `*:8080` line. If not, the compose changed under your feet — check it matches [`../../stack/docker-compose.yml`](../../stack/docker-compose.yml).

3. **Different port?** The repo currently uses `network_mode: host` and exposes port **8080**. Older versions of this README used `3000` — make sure you're hitting the right one. Browse to <http://127.0.0.1:8080>.

4. **Windows browser can't reach Linux port?** Confirm `.wslconfig` has `networkingMode=mirrored` (see [setup/01-windows-host.md](../setup/01-windows-host.md)). If you can only reach via the WSL IP (`wsl hostname -I`), mirrored mode isn't active — `wsl --shutdown` from PowerShell and try again.

## ollama not reachable on `:11434`

```bash
systemctl is-active ollama          # → active
ss -tlnp | grep 11434                # → 0.0.0.0:11434 listening
journalctl -u ollama -n 50 --no-pager
```

Common causes:

- **Listening on `127.0.0.1` only** — the override.conf wasn't applied. Re-do step 3.2 in [setup/03-ollama.md](../setup/03-ollama.md) and `sudo systemctl daemon-reload && sudo systemctl restart ollama`.
- **Service not started** — `sudo systemctl enable --now ollama`.
- **Different distro** — make sure you're checking the WSL distro that runs ollama (Earth-AI), not the dev distro.

## GPU not utilized (slow generation, fans quiet)

Quick triage:

```bash
nvidia-smi                          # is the GPU even visible?
nvidia-smi -q | grep -i 'cuda'      # CUDA driver version
ollama ps                           # is the model actually loaded?
```

If `nvidia-smi` shows the model using ~12 GB+ of VRAM but 0% utilization, **the model is loaded but idle** — generation speed is the actual test, not the utilization snapshot. Try a real prompt:

```bash
time ollama run qwen2.5-coder:14b "write a haiku about boats"
```

You should see GPU fans spool and a response in 1–3 seconds. If it takes 30 seconds, something is wrong.

Likely fixes:

1. **Stale driver** — install the latest NVIDIA driver on Windows, then `wsl --shutdown` and reopen.
2. **`LD_LIBRARY_PATH` lost on a custom build** — uncomment the line in `override.conf`:
   ```ini
   Environment="LD_LIBRARY_PATH=/usr/lib/wsl/lib"
   ```
   then `sudo systemctl daemon-reload && sudo systemctl restart ollama`.
3. **Model overflowed VRAM** — `qwen2.5-coder:32b` needs more than 16 GB and will spill into system RAM. Switch to `qwen2.5-coder:14b` or the `:32b-instruct-q2_K` variant.

## "Model not found" from a client

The client is using a model name LiteLLM doesn't know about. Check the alias list:

```bash
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  | python3 -m json.tool | grep '"id"'
```

If your model isn't in the output, add it to `litellm/config.yaml` and restart LiteLLM:

```bash
cd ~/src/jomkz/earth-ai/stack
docker compose restart litellm
```

## LiteLLM smoke test fails

```bash
cd ~/src/jomkz/earth-ai/stack
./scripts/smoke.sh
```

If it errors, work through these in order:

1. **`.env` missing or wrong perms** — `ls -la .env` should show `-rw-------`. Re-run `./scripts/generate-env.sh` to regenerate (then re-do `init-billing-table.sh`).
2. **Containers down** — `docker compose ps`; `docker compose up -d`.
3. **Backend keys missing** — open `stack/.env` and confirm `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` are filled in for the providers you expect to use. Then `docker compose restart litellm` to reload the values.
4. **Network host mode** — LiteLLM uses `network_mode: host` so it can reach ollama on `127.0.0.1`. If your distro doesn't permit host-mode networking, the container will start but calls to `/v1/chat/completions` with `ollama/*` models will time out.

## Grafana shows no data

1. **Datasource broken** — Configuration → Data sources → Postgres → **Save & Test**. If it fails, check the `POSTGRES_PASSWORD` matches between `.env` and Grafana's provisioned datasource.
2. **Time range too narrow** — top-right corner; switch to "Last 30 days".
3. **No calls have been made yet** — run `./scripts/smoke.sh` and refresh.

## "Cannot find name `john`" or similar — wrong default user in WSL

Symptom: WSL terminal opens as `root`, or `~` resolves to `/root`.

Fix `/etc/wsl.conf`:

```ini
[boot]
systemd=true

[user]
default=john
```

Then `wsl --shutdown` from PowerShell and reopen.

## Provisioner failed partway

`provision.sh` is idempotent — safe to re-run. If a step fails, fix the immediate cause (often: network glitch on `apt`, or an `ollama pull` interrupted) and run it again. It will skip work that's already done.

If something is wedged, you can also run a single phase by hand using the corresponding doc under [setup/](../setup/).
