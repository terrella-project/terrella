# Runbook — earth data rescue & restore for the Fedora migration

One-time record of the M0 data migration ([epic #3](https://github.com/terrella-project/terrella/issues/3)):
rescuing the WSL-era stack data from the old Windows install (#5) and restoring it into the
terrella quadlet stack (#9). Kept as a runbook so the procedure survives for the next machine
— and because the podman-native restore commands become the template for
[maintenance.md](../operations/maintenance.md)'s backup/restore section.

## Part 1 — offline data rescue from the mounted Windows disk (#5)

The old Windows/WSL install stayed bootable, but booting it was unnecessary: with the Windows
NTFS disk mounted read-only under Fedora, the WSL distro's `ext4.vhdx` can be mounted directly
with libguestfs. **All access is read-only — the old install remains a pristine fallback.**

### 1. Locate and mount the distro image

WSL2 distro filesystems live at `C:\Users\<user>\AppData\Local\wsl\{guid}\ext4.vhdx`
(store-installed distros use `...\Packages\<distro>\LocalState\ext4.vhdx`). Identify the right
one by size, then confirm by hostname after mounting. The vhdx contains a bare ext4 filesystem
on the whole virtual disk — no partition table, so the mount device is `/dev/sda`:

```bash
sudo dnf install guestfs-tools   # guestmount / virt-filesystems (already present on earth)
export LIBGUESTFS_BACKEND=direct # the libvirt backend cannot traverse the fuse NTFS mount
VHDX="/run/media/john/Windows Disk/Users/John/AppData/Local/wsl/{7bf1aa41-…}/ext4.vhdx"
virt-filesystems -a "$VHDX" --all --long          # expect: /dev/sda ext4
mkdir -p ~/wsl-rescue-mnt
guestmount --ro -a "$VHDX" -m /dev/sda ~/wsl-rescue-mnt
cat ~/wsl-rescue-mnt/etc/hostname                  # confirm: earth (the Earth-AI distro)
```

For bulk copies (the ~109 GB ollama model store), `sudo qemu-nbd -r -c /dev/nbd0 "$VHDX"` +
`mount -o ro /dev/nbd0 /mnt` is considerably faster than fuse; `guestmount` was fast enough
in practice for everything else.

### 2. Extract the data

Into `~/wsl-backup/`. What lives where (WSL-era layout, per `stack/docker-compose.yml`):

| Data | Location inside the image |
|---|---|
| Secrets (`.env`) | `/home/john/src/jomkz/earth-ai/stack/.env` |
| Postgres data dir (bind mount) | `.../stack/data/postgres` |
| Grafana data dir (bind mount) | `.../stack/data/grafana` |
| Open WebUI volume | `/var/lib/docker/volumes/earth-ai_open-webui/_data` |
| Prometheus TSDB volume | `/var/lib/docker/volumes/earth-ai_prometheus-data/_data` |
| ollama models | `/usr/share/ollama/.ollama/models` (~109 GB) |
| Image versions at cutover | `/var/lib/docker/containers/*/config.v2.json` |

```bash
SRC=~/wsl-rescue-mnt/home/john/src/jomkz/earth-ai/stack
install -m 600 "$SRC/.env" ~/wsl-backup/env.backup
cp -a "$SRC/data/postgres" ~/wsl-backup/pgdata-copy
tar cf ~/wsl-backup/grafana-data.tar    -C "$SRC/data/grafana" .
tar cf ~/wsl-backup/open-webui.tar      -C ~/wsl-rescue-mnt/var/lib/docker/volumes/earth-ai_open-webui/_data .
tar cf ~/wsl-backup/prometheus-data.tar -C ~/wsl-rescue-mnt/var/lib/docker/volumes/earth-ai_prometheus-data/_data .
cp -r  ~/wsl-rescue-mnt/usr/share/ollama/.ollama/models ~/.ollama/models   # direct to final home
```

**`env.backup` is the crown jewel**: `LITELLM_SALT_KEY` decrypts the provider keys LiteLLM
stores in Postgres (`STORE_MODEL_IN_DB=True`). A Postgres restore without the original salt
key is crippled. Never regenerate it (`generate-env.sh --force` would) — carry it forward
verbatim.

### 3. Dump Postgres from a throwaway container

Raw PGDATA is never restored into the new stack (rootless uid mapping and locale drift make
file-level restores fragile — dump/restore is the portable path). The copied data dir was
last written by an unclean WSL shutdown; Postgres WAL crash-recovery handles that on startup:

```bash
podman run -d --name pg-rescue \
  -v ~/wsl-backup/pgdata-copy:/var/lib/postgresql/data:Z docker.io/library/postgres:16
podman exec pg-rescue pg_isready -U litellm        # wait for recovery to finish
podman exec pg-rescue psql -U litellm -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE NOT datistemplate"   # postgres, litellm, openwebui
podman exec pg-rescue pg_dump -U litellm -d litellm   | gzip > ~/wsl-backup/litellm.sql.gz
podman exec pg-rescue pg_dump -U litellm -d openwebui | gzip > ~/wsl-backup/openwebui.sql.gz
podman rm -f pg-rescue
```

### 4. Verify readability and record the baseline

Done **before anything else in M0** — a backup that can't be read back is not a backup:

```bash
gunzip -t ~/wsl-backup/*.sql.gz
tar tf ~/wsl-backup/open-webui.tar | head
grep -c LITELLM_SALT_KEY ~/wsl-backup/env.backup
```

Baseline row counts recorded to `~/wsl-backup/baseline-rowcounts.txt` for post-restore
comparison (from the pg-rescue container, 2026-07-09):

| Table | Rows | Notes |
|---|---|---|
| `litellm."LiteLLM_SpendLogs"` | 37 711 | spend history through 2026-05-12 |
| `openwebui.chat` | 22 | the live chat store (see below) |
| `openwebui."user"` | 1 | |

### 5. Findings that changed downstream issues

- **#8 resolved — Open WebUI's real store is Postgres.** The `openwebui` database exists in
  PGDATA and holds 22 chats; the `webui.db` SQLite file inside the volume is a stale
  pre-cutover leftover (last write 2026-04-27, 4 chats). The quadlet stack keeps
  `DATABASE_URL` pointed at the dedicated `openwebui` DB; the volume tarball still matters
  for `uploads/` and `vector_db/`.
- **No WSL benchmark baseline exists in Postgres.** Neither `benchmark_results` nor
  `monthly_costs` was ever created on the old install (the init scripts never ran;
  `benchmark-models.py` silently skips persistence without psycopg2). #13's "compare vs WSL"
  will use the benchmark report's *Hist* columns, which are computed from the restored
  `LiteLLM_SpendLogs` history instead.
- **The model store is ~109 GB, not the ~44 GB the docs suggested** — the general-purpose
  tail in `provision/models.list` adds up. Copying from the mounted image cost no bandwidth;
  the set gets pruned to the curated list when ollama comes up (#12).
- Cutover image versions (from `config.v2.json`, for pinning the quadlets): postgres `16`,
  open-webui `main@sha256:c2e4723f…`, litellm `main-stable@sha256:9e1536c6…`, grafana
  `latest@sha256:0f86bada…`, prometheus `latest@sha256:e4254400…`, github-mcp
  `latest@sha256:2ac27ef0…`, exporters `python:3.12-slim@sha256:46cb7cc2…`.

### 6. Unmount

```bash
guestunmount ~/wsl-rescue-mnt
```

The vhdx on the Windows disk remains the untouched master copy until #78 retires the old
install.

## Part 2 — restore into the terrella quadlet stack (#9)

*Lands with the quadlet stack (#7/#9). Outline: start `terrella-postgres` alone (LiteLLM must
not run its schema migrations against an empty DB first), `createdb openwebui`, pipe both
dumps through `podman exec -i terrella-postgres psql`, `podman volume import` the open-webui
and grafana tarballs, seed the new `.env` from `env.backup` verbatim, then start
`terrella.target` and compare row counts against `baseline-rowcounts.txt`.*
