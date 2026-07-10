# Maintenance

Day-to-day operations on the running stack.

## Gaming toggle

ollama keeps models loaded in VRAM for fast first-token latency, which steals frames from
any 3D game on the same GPU. The stack is grouped under systemd targets (#11, ADR-0002),
so freeing the GPU is one command — this replaces the WSL-era `wsl --shutdown`.

### Gaming Mode — free the VRAM

```bash
systemctl --user stop terrella-inference.target
```

Stops the VRAM holders (host ollama, LiteLLM, Open WebUI) and **releases all model VRAM**
(measured on earth: 10.8 GB → 1.5 GB desktop baseline). Prometheus, Grafana, Postgres,
and the exporters keep running — metrics and the spend ledger stay live.

To take the whole stack down instead:

```bash
systemctl --user stop terrella.target
```

### AI Mode — bring it back

```bash
systemctl --user start terrella-inference.target   # or terrella.target for everything
```

Both targets also start automatically at boot (user lingering +
`WantedBy=default.target`), so a reboot lands in AI Mode.

Check what's holding the GPU at any time:

```bash
nvidia-smi --query-gpu=memory.used --format=csv,noheader
ollama ps
```

---

## Backup / restore Open WebUI

The Open WebUI database (chats, settings, users) lives in the named Docker volume `open-webui`. Back it up before upgrades and on a regular cadence.

### Backup

```bash
cd ~  # or wherever you want the tarball saved
docker run --rm \
  -v open-webui:/data \
  -v "$(pwd)":/backup \
  alpine \
  tar czf "/backup/openwebui_backup_$(date +%Y%m%d).tar.gz" /data
```

Result: a file like `openwebui_backup_20260427.tar.gz` in the current directory.

### Restore

```bash
docker run --rm \
  -v open-webui:/data \
  -v "$(pwd)":/backup \
  alpine \
  sh -c "rm -rf /data/* && tar xzf /backup/openwebui_backup_20260427.tar.gz -C /"
```

> Replace the filename with whichever backup you want to restore. The container wipes the volume contents before extracting, so you get an exact restore (not a merge).

---

## Backup the observability stack

Postgres holds the per-call cost log and the `monthly_costs` table. Back it up the same way:

```bash
cd ~/src/jomkz/terrella/stack
docker compose exec -T postgres pg_dump -U litellm litellm \
  | gzip > "litellm_pg_$(date +%Y%m%d).sql.gz"
```

Restore (with the stack stopped):

```bash
gunzip -c litellm_pg_20260427.sql.gz \
  | docker compose exec -T postgres psql -U litellm litellm
```

---

## Adding / removing baseline models

The set of models the provisioner pulls is in [`provision/models.list`](../../provision/models.list). To change the baseline:

```bash
cd ~/src/jomkz/terrella
$EDITOR provision/models.list
bash provision/provision.sh        # pulls anything new (idempotent)

# To actually drop a model from disk, also remove it by hand:
ollama rm <model-name>

git add provision/models.list
git commit -m "Models: add foo, drop bar"
```

The provisioner never deletes — that's deliberate, so a typo or merge can't wipe gigabytes of weights. See [reference/local-models.md](../reference/local-models.md) for what each model is for and the heuristics for picking one.

To inspect what's currently installed:

```bash
ollama list                                    # quick listing
curl -s http://localhost:11434/api/tags \
  | python3 -m json.tool                       # full JSON with sizes/quants
```

To check whether anything in your LiteLLM config is stale or what new provider models have been released, run [`stack/scripts/list-models.sh`](../../stack/scripts/list-models.sh) — it diffs the live API model lists (Anthropic, Gemini, OpenAI, ollama) against `litellm/config.yaml`. For OpenAI, it intentionally compares against a curated set of stable core chat/reasoning model IDs so snapshots and specialized audio/image/realtime variants do not drown the signal.

To refresh the managed provider catalogs in-place, run:

```bash
cd ~/src/jomkz/terrella/stack
./scripts/update-litellm-config.sh --dry-run   # preview
./scripts/update-litellm-config.sh             # write changes
docker compose restart litellm
```

That script updates the marked catalog blocks for Anthropic, Gemini, OpenAI, and ollama while leaving your hand-edited aliases and non-model settings alone.

---

## Updating ollama models

ollama does **not** auto-update. Pull the latest version of every installed model with:

```bash
cd ~/src/jomkz/terrella
./stack/scripts/update-ollama-models.sh             # re-pulls all installed + adds anything in models.list
./stack/scripts/update-ollama-models.sh --installed-only   # skip models.list; only re-pull existing
```

`./stack/scripts/list-models.sh ollama` shows current sizes and any locally-installed models not in `litellm/config.yaml`.

---

## Updating containers

```bash
cd ~/src/jomkz/terrella/stack
docker compose pull
docker compose up -d
```

> `docker compose pull` only re-downloads images. The named volumes (`open-webui`, the Postgres data dir) are preserved across container recreation.

---

## Updating ollama itself

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl restart ollama
```

The systemd drop-in at `/etc/systemd/system/ollama.service.d/override.conf` is preserved across upgrades — that's why we put the `OLLAMA_HOST` / `OLLAMA_ORIGINS` config there in [ollama setup](../setup/03-ollama.md).

---

## Pruning unused Docker stuff

Periodically reclaim disk:

```bash
docker image prune -f                # dangling images
docker container prune -f            # stopped containers
docker volume ls                     # inspect before pruning volumes!
```

Don't run `docker volume prune` blindly — it would wipe `open-webui` and the Postgres volume.

---

## Checking GPU / VRAM at any time

```bash
nvidia-smi
```

- `Processes` section: which processes own VRAM right now.
- `Memory-Usage`: total VRAM in use vs available.
- Combined with `ollama ps` (lists models currently loaded), this tells you whether ollama is keeping a large model warm.

To force ollama to free VRAM **without** restarting the service:

```bash
ollama stop <model-name>
# or simply unload by sending an empty prompt to a different model
```
