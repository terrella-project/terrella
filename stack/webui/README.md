# `stack/webui/`

Docker-compose project: **Open WebUI** — the browser-based chat interface that talks to ollama (and optionally cloud providers configured in its settings).

Project name: `earth-ai` (kept from when this compose file lived at the repo root, so the existing `earth-ai_open-webui` volume keeps working).

## Run

```bash
cd ~/src/jomkz/earth-ai/stack/webui
docker compose up -d
```

Open: <http://127.0.0.1:8080>.

The first user to register becomes the admin. See [`../../docs/setup/04-open-webui.md`](../../docs/setup/04-open-webui.md) for the full first-run walkthrough.

## Why `network_mode: host`

So the container's `127.0.0.1` is the WSL distro's `127.0.0.1`, which is also Windows's `127.0.0.1` thanks to mirrored networking. Result: zero NAT, ollama is reachable as `http://127.0.0.1:11434` with no extra plumbing.

## Backup / restore

→ [`../../docs/operations/maintenance.md#backup--restore-open-webui`](../../docs/operations/maintenance.md#backup--restore-open-webui).

## Update

```bash
cd ~/src/jomkz/earth-ai/stack/webui
docker compose pull
docker compose up -d
```

The named volume is preserved across container recreation, so chats and settings survive upgrades.
