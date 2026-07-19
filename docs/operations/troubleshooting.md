# Troubleshooting

Symptoms first, then likely causes and fixes. The stack runs as rootless podman quadlets
under the login user — most answers start with `systemctl --user` and `journalctl --user`.

## A service is down / won't start

```bash
systemctl --user status terrella-<service>.service     # state + last log lines
journalctl --user -u terrella-<service>.service -n 100 --no-pager
podman ps -a --filter name=terrella                    # container-level view
```

Common causes:

- **Unit edited but not reloaded** — after touching anything in `stack/quadlet/`, run
  `stack/quadlet/install.sh && systemctl --user daemon-reload`, then restart the unit.
- **`start request repeated too quickly`** — the unit crash-looped into systemd's rate
  limit. Read the journal for the real error, fix it, then
  `systemctl --user reset-failed terrella-<service>.service` and start again.
- **Missing env file** — the units read `~/.config/terrella/env.d/*.env`; if the stack was
  never installed on this machine, run `stack/quadlet/install.sh` (needs `stack/.env`).

## Open WebUI won't load in the browser

1. **Is the unit up?** `systemctl --user status terrella-openwebui.service`.
2. **Is port 8080 listening?** `ss -tln | grep 8080` — expected `127.0.0.1:8080`
   (loopback only; remote access is via the tailnet, not the LAN).
3. Browse to <http://127.0.0.1:8080>.

## ollama not reachable on `:11434`

```bash
systemctl --user is-active ollama       # → active (user unit, not system!)
ss -tln | grep 11434                     # → 0.0.0.0:11434 listening
journalctl --user -u ollama -n 50 --no-pager
```

Common causes:

- **Checking the wrong manager** — ollama is a **user** service
  (`stack/quadlet/ollama.service`); `sudo systemctl status ollama` finds nothing.
- **Listening on `127.0.0.1` only** — containers reach the host via
  `host.containers.internal`, which **cannot** see loopback-bound listeners (see
  `stack/quadlet/README.md`). The unit must keep `OLLAMA_HOST=0.0.0.0`; the LAN side is
  firewalld's job.
- **Stopped by the gaming toggle** — `systemctl --user start terrella-inference.target`.

## Containers can't reach host ollama (`ollama/*` models time out)

```bash
podman exec terrella-litellm python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://host.containers.internal:11434/api/version', timeout=3).read())"
```

- **Name doesn't resolve** — pasta's `--map-guest-addr` provides
  `host.containers.internal` on podman ≥ 5.3; check `podman version` and
  `getent hosts host.containers.internal` inside a container.
- **Resolves but times out** — ollama is loopback-bound (above) or a firewalld change
  started filtering pasta traffic; re-test with `curl` from a throwaway container and see
  the fallbacks in `stack/quadlet/README.md` (`--map-host-loopback`, tailnet address).

## Inter-service errors after config edits (connection refused between services)

Services talk over the `terrella` network using **container DNS names and in-network
ports** (`terrella-postgres:5432`, `terrella-prometheus:9090`). A config pointing at
`127.0.0.1:<port>` or `localhost` is wrong inside a container — pasta does not hairpin
host-published loopback ports back into containers. Every rendered config comes from
`stack/quadlet/install.sh`; fix the source, re-run it, restart the service.

## GPU not utilized (slow generation, fans quiet)

Quick triage:

```bash
nvidia-smi                          # is the GPU even visible?
ollama ps                           # is the model actually loaded, and "100% GPU"?
```

If `nvidia-smi` shows the model using ~12 GB+ of VRAM but 0% utilization, **the model is
loaded but idle** — generation speed is the actual test, not the utilization snapshot:

```bash
time ollama run qwen2.5-coder:14b "write a haiku about boats"
```

You should see GPU fans spool and a response in 1–3 seconds. If it takes 30 seconds:

1. **Model overflowed VRAM** — `qwen2.5-coder:32b` needs more than 16 GB and spills into
   system RAM (`ollama ps` shows a CPU percentage). Switch to `qwen2.5-coder:14b` or the
   `:32b-instruct-q2_K` variant.
2. **Driver problem after a kernel update** — akmods rebuilds the module at boot; check
   `modinfo -F version nvidia` and `journalctl -b -u akmods`. The loaded module must be
   the **open** flavor (`modinfo -F license nvidia` → `Dual MIT/GPL`) on Blackwell.

## SELinux denials on bind mounts

Symptom: a container exits with `permission denied` reading a mounted config;
`sudo ausearch -m avc -ts recent` shows denials.

Config mounts out of `~/.config/terrella/` carry `:Z` in the quadlet units (private
relabel). If you add a mount, keep the pattern — and never `:Z` a directory shared with
anything else (it relabels the source).

## Restored volume: service crashes with "readonly database" / permission errors

The tarball's `./` entry can overwrite the volume root's owner on `podman volume import`.
Fix per the migration runbook:

```bash
podman unshare chown <container-uid>:0 ~/.local/share/containers/storage/volumes/<volume>/_data
```

(Grafana is uid 472; Open WebUI runs as container root and is unaffected.)

## "Model not found" from a client

The client is using a model name LiteLLM doesn't know about. Check the alias list:

```bash
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  | python3 -m json.tool | grep '"id"'
```

If your model isn't in the output, refresh the managed LiteLLM catalog and re-render:

```bash
cd ~/src/terrella/stack
./scripts/update-litellm-config.sh
./quadlet/install.sh
systemctl --user restart terrella-litellm.service
```

## LiteLLM smoke test fails

```bash
cd ~/src/terrella/stack
./scripts/smoke.sh
```

If it errors, work through these in order:

1. **`.env` missing or wrong perms** — `ls -la .env` should show `-rw-------`. On a
   machine with restored data, **never** regenerate it (`generate-env.sh --force` mints a
   new `LITELLM_SALT_KEY` and bricks the provider keys stored in Postgres).
2. **Units down** — `systemctl --user start terrella.target`.
3. **Backend keys missing** — check `stack/.env`, then `stack/quadlet/install.sh` (re-splits
   `env.d/`) and `systemctl --user restart terrella-litellm.service` — env files are read
   at container creation, so a restart is required.

## Grafana shows no data

1. **Datasource broken** — Configuration → Data sources → Postgres → **Save & Test**. If
   it fails, check `POSTGRES_PASSWORD` matches between `stack/.env` and
   `~/.config/terrella/env.d/grafana.env` (re-run `install.sh` after `.env` changes).
2. **Time range too narrow** — top-right corner; switch to "Last 30 days".
3. **No calls have been made yet** — run `./scripts/smoke.sh` and refresh.

## Stack didn't start after reboot

Lingering must be on and the targets enabled:

```bash
loginctl show-user "$USER" -p Linger    # → Linger=yes (else: sudo loginctl enable-linger $USER)
systemctl --user is-enabled terrella.target terrella-inference.target ollama.service
```

`stack/quadlet/install.sh` enables all three; quadlet-generated container units are wired
by the generator automatically.

## Provisioner failed partway

`provision/fedora/bootstrap.sh` is idempotent — safe to re-run (`--check` shows what it
would do). Fix the immediate cause (usually a network glitch on `dnf` or a repo outage)
and run it again; completed steps are detected and skipped.
