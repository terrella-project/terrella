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

## Backup / restore volumes (Open WebUI, Grafana)

Open WebUI's uploads/vector store live in the named podman volume `terrella-openwebui`
(chats are in Postgres — see below); Grafana's users/prefs/annotations in
`terrella-grafana`. `podman volume export/import` replaces the old alpine-tar dance:

### Backup

```bash
podman volume export terrella-openwebui > "openwebui_backup_$(date +%Y%m%d).tar"
podman volume export terrella-grafana  > "grafana_backup_$(date +%Y%m%d).tar"
```

### Restore

```bash
systemctl --user stop terrella-openwebui.service   # or terrella-grafana.service
podman volume import terrella-openwebui openwebui_backup_20260709.tar
systemctl --user start terrella-openwebui.service
```

> `import` replaces the volume contents (exact restore, not a merge). If the restored
> service fails with permission errors, the tarball's `./` entry may have overwritten the
> volume root's owner — see the fix in
> [runbooks/fedora-migration.md](../runbooks/fedora-migration.md) (`podman unshare chown`).

---

## Backup the databases

Postgres holds the per-call cost log (`litellm` DB) and Open WebUI's chats/settings/users
(`openwebui` DB):

```bash
podman exec terrella-postgres pg_dump -U litellm -d litellm \
  | gzip > "litellm_pg_$(date +%Y%m%d).sql.gz"
podman exec terrella-postgres pg_dump -U litellm -d openwebui \
  | gzip > "openwebui_pg_$(date +%Y%m%d).sql.gz"
```

Restore (into an empty database — stop the stack, keep only postgres up):

```bash
systemctl --user stop terrella.target
systemctl --user start terrella-postgres.service
gunzip -c litellm_pg_20260709.sql.gz | podman exec -i terrella-postgres psql -U litellm -d litellm
systemctl --user start terrella.target
```

---

## Adding / removing baseline models

The set of models the provisioner pulls is in [`provision/models.list`](../../provision/models.list). To change the baseline:

```bash
cd ~/src/terrella
$EDITOR provision/models.list
bash provision/sync-models.sh      # pulls anything new (idempotent)

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
cd ~/src/terrella/stack
./scripts/update-litellm-config.sh --dry-run   # preview
./scripts/update-litellm-config.sh             # write changes
./quadlet/install.sh                           # re-render ~/.config/terrella
systemctl --user restart terrella-litellm.service
```

That script updates the marked catalog blocks for Anthropic, Gemini, OpenAI, and ollama while leaving your hand-edited aliases and non-model settings alone.

---

## Updating ollama models

ollama does **not** auto-update. Pull the latest version of every installed model with:

```bash
cd ~/src/terrella
./stack/scripts/update-ollama-models.sh             # re-pulls all installed + adds anything in models.list
./stack/scripts/update-ollama-models.sh --installed-only   # skip models.list; only re-pull existing
```

`./stack/scripts/list-models.sh ollama` shows current sizes and any locally-installed models not in `litellm/config.yaml`.

---

## Updating containers

Images are **pinned to exact version tags** in the quadlet units — no `:latest`, no
auto-update (the units are the M1 renderer's golden fixtures; updates are deliberate):

```bash
cd ~/src/terrella
$EDITOR stack/quadlet/terrella-<service>.container    # bump the Image= tag
stack/quadlet/install.sh                              # copies units, pulls the new image
systemctl --user daemon-reload
systemctl --user restart terrella-<service>.service
```

> Named volumes (`terrella-postgres`, `terrella-openwebui`, `terrella-grafana`,
> `terrella-prometheus`) are preserved across container recreation. Take a DB/volume
> backup before major-version bumps.

---

## Updating ollama itself

ollama runs from the official release tarball under `~/.local` as a systemd **user**
service (no root install):

```bash
VER=v0.31.2   # pick the target release
curl -fL -o /tmp/ollama.tar.zst \
  "https://github.com/ollama/ollama/releases/download/$VER/ollama-linux-amd64.tar.zst"
systemctl --user stop ollama.service
tar --use-compress-program=unzstd -xf /tmp/ollama.tar.zst -C ~/.local
systemctl --user start ollama.service
ollama --version
```

The `OLLAMA_HOST` / `OLLAMA_ORIGINS` settings live in the unit itself
(`stack/quadlet/ollama.service`), so upgrades can't clobber them.

---

## Pruning unused podman stuff

Periodically reclaim disk:

```bash
podman image prune -f                # dangling images
podman container prune -f            # stopped containers
podman volume ls                     # inspect before pruning volumes!
```

Don't run `podman volume prune` blindly — it would wipe the `terrella-*` data volumes.

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
