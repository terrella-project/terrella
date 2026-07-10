# terrella quadlet stack

Hand-written podman Quadlet units for the terrella stack on Fedora (M0, epic #3;
ADR-0002/ADR-0008). These files are the **golden reference** the M1 renderer must reproduce
byte-equivalently (#18) — treat every line as a rendering decision.

## Architecture

Everything runs **rootless under the login user** (decision D1; per-service rootful from
`/etc/containers/systemd/` is the ADR-0002 escape hatch, unused). `loginctl enable-linger`
makes the stack start at boot and survive logout.

| Unit | Image (pinned — D5) | Published (loopback only) | Target |
|---|---|---|---|
| `terrella-postgres` | `postgres:16.14` | `127.0.0.1:5433→5432` | terrella |
| `terrella-litellm` | `litellm:v1.83.14-stable` | `127.0.0.1:4000` | terrella-inference |
| `terrella-openwebui` | `open-webui:v0.10.2` | `127.0.0.1:8080` | terrella-inference |
| `terrella-grafana` | `grafana:13.1.0` | `127.0.0.1:3000` | terrella |
| `terrella-prometheus` | `prometheus:v3.13.0` | `127.0.0.1:9090` | terrella |
| `terrella-litellm-exporter` | `python:3.12.13-slim` | `127.0.0.1:11436` | terrella |
| `terrella-ollama-exporter` | `python:3.12.13-slim` | `127.0.0.1:11435` | terrella |
| `terrella-github-mcp` | `github-mcp-server:v1.5.0` | `127.0.0.1:8765` | terrella |
| `ollama.service` (host binary, user unit — #12) | — | `0.0.0.0:11434` (firewalled, #10) | terrella-inference |

Targets: `terrella.target` (whole stack, `WantedBy=default.target`) wants
`terrella-inference.target` (the VRAM holders). Every member sets `PartOf=` so stops
cascade. **Gaming toggle:** `systemctl --user stop terrella-inference.target` frees the GPU
while observability keeps running; stopping `terrella.target` takes everything down.

Readiness: `terrella-postgres` carries the only hard health gate (`HealthCmd=pg_isready` +
`Notify=healthy`), replacing compose's `service_healthy`; consumers use plain
`Requires=`/`After=`.

### Rendered artifacts and secrets (`install.sh`)

`install.sh` performs, by hand, exactly what the M1 renderer will do (ADR-0006):

- **Rendered configs → `~/.config/terrella/`**: the LiteLLM `config.yaml` comes from the
  legacy tree with one transform (`127.0.0.1:11434` → `host.containers.internal:11434`);
  `prometheus.yml` and Grafana's `datasources.yml` are quadlet-specific copies under
  `config/` (container-DNS targets); Grafana dashboards and the exporter `.py` files copy
  unchanged. Units reference `%h/.config/terrella/...`, never the repo checkout.
- **Secrets**: `stack/.env` splits into per-service `~/.config/terrella/env.d/*.env`
  (mode 600) consumed via `EnvironmentFile=` — no container sees another service's keys.
  Podman secrets + sops-age arrive at M2 (#27).
- **Units**: per-file symlinks into `~/.config/containers/systemd/` (quadlets) and
  `~/.config/systemd/user/` (targets), then `daemon-reload`.
- **Images**: pre-pulled at install; **no `AutoUpdate=`** — updating means editing the
  pinned tag, re-running `install.sh`, and restarting the unit (golden files stay
  reproducible).

### Update workflow

```bash
# edit the Image= pin in the unit (or any config under config/), then
stack/quadlet/install.sh
systemctl --user daemon-reload
systemctl --user restart terrella-<service>.service
```

## Golden-fixture status

These hand-written files are the reference output for the M1 renderer's golden tests
(#18): `terrella apply` must reproduce them byte-equivalently from `terrella.yaml` before
the legacy `stack/` and `provision/` trees are deleted (#81).

The units land with #7. This README currently records the networking pattern from the #6
spike, which every unit depends on.

## Networking pattern (spike #6 — measured on earth, 2026-07-09)

Environment: podman 5.8.3, netavark backend, pasta 0^20260611 (rootless), SELinux enforcing,
firewalld active (default `FedoraWorkstation` zone on `wlo1`).

All containers join the named bridge network `terrella` (aardvark-dns provides
container-name DNS). Host networking is gone (ADR-0002), which raises two questions the
spike answered:

### Containers → host ollama (`:11434`)

**Pattern: `http://host.containers.internal:11434`.** With podman ≥ 5.3, pasta maps the
host as `169.254.1.2` (`--map-guest-addr` default) and injects the
`host.containers.internal` hosts entry into every container on a named network.

| Test | Result |
|---|---|
| `getent hosts host.containers.internal` in a container on the `terrella` network | `169.254.1.2` ✅ |
| `curl http://host.containers.internal:11434` → host listener bound `0.0.0.0` | HTTP 200 ✅ (with firewalld active) |
| Same, host listener bound `127.0.0.1` only | unreachable ❌ (HTTP 000, timeout) |

Consequences:

- **ollama must bind `0.0.0.0`** (the existing `OLLAMA_HOST=0.0.0.0` drop-in pattern
  carries over to the Fedora user unit, #12); the LAN is closed by firewalld zones (#10),
  not by loopback binding.
- Everything that talks to ollama uses a single swappable env var / config value:
  `OLLAMA_BASE_URL=http://host.containers.internal:11434` (open-webui, ollama-exporter,
  and every `api_base:` in the LiteLLM `config.yaml`).

Fallbacks, in order, if the pattern breaks (e.g. pasta regression):
(a) `pasta_options = ["--map-host-loopback"]` in `~/.config/containers/containers.conf`
lets containers reach host loopback; (b) point clients at earth's tailnet address (couples
container start to tailscaled); (c) run the affected unit rootful from
`/etc/containers/systemd/` (ADR-0002 escape hatch).

### Container ↔ container: names only, never published ports

Ports are published on `127.0.0.1` for host access, but **pasta does not hairpin published
loopback ports back to containers**:

| Test | Result |
|---|---|
| host → `127.0.0.1:8099` (published from container) | HTTP 200 ✅ |
| container → `host.containers.internal:8099` (same published port) | unreachable ❌ |
| container → `spike-web:80` (container DNS name, in-network port) | HTTP 200 ✅ |

Consequence: **inter-service config must use container DNS names and in-network ports**
(`terrella-postgres:5432`, `terrella-prometheus:9090`, `terrella-litellm:4000`), never the
WSL-era `127.0.0.1:<published>` form. Every `localhost` in `prometheus.yml`, Grafana's
`datasources.yml`, and service env vars gets retargeted in #7.

### Deferred checks — both verified 2026-07-10 with #4/#10 applied

- [x] `tailscale serve --bg --tcp 4000 tcp://127.0.0.1:4000` forwards through the
      pasta-published loopback port into the container — `earth:4000/health/liveness`,
      `earth:11434/api/version`, and `earth:3000/api/health` all answer over the tailnet.
- [x] Container → `host.containers.internal:11434` still passes with the `terrella-lan`
      zone active (Fedora Workstation's `1025-65535` open range closed) — pasta traffic
      does not traverse the LAN zone. HTTP 200.
