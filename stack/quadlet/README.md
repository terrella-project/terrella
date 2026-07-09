# terrella quadlet stack

Hand-written podman Quadlet units for the terrella stack on Fedora (M0, epic #3;
ADR-0002/ADR-0008). These files are the **golden reference** the M1 renderer must reproduce
byte-equivalently (#18) — treat every line as a rendering decision.

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

### Still to verify (blocked on tailscale install, #4/#10)

- [ ] `tailscale serve --bg --tcp 4000 tcp://127.0.0.1:4000` forwards through the
      pasta-published loopback port into the container.
- [ ] Container → `host.containers.internal:11434` still passes once #10 replaces the
      default `FedoraWorkstation` zone (its `1025-65535` open range must go).
