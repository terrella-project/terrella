# `stack/observability/`

Config files for the LiteLLM, Prometheus, and Grafana services. These are mounted read-only into the containers defined in [`../docker-compose.yml`](../docker-compose.yml).

| Directory | Mounted into |
|---|---|
| `litellm/config.yaml` | `litellm` container |
| `prometheus/prometheus.yml` | `prometheus` container |
| `grafana/provisioning/` | `grafana` container |

The compose file, `.env`, scripts, and SQL all live one level up in [`stack/`](../).

Documentation:

| You want to… | Read |
|---|---|
| Install and bring the stack up | [`../../docs/setup/06-observability-stack.md`](../../docs/setup/06-observability-stack.md) |
| Log monthly Copilot / Claude bills | [`../../deploy/earth/manual-billing.md`](../../deploy/earth/manual-billing.md) |
| Reach this stack from another machine | [`../../docs/operations/cross-machine-access.md`](../../docs/operations/cross-machine-access.md) |
| Diagnose a broken stack | [`../../docs/operations/troubleshooting.md`](../../docs/operations/troubleshooting.md) |

Quick start (assumes you've read the setup doc):

```bash
cd ~/src/terrella/stack
./scripts/generate-env.sh        # first time only
docker compose up -d
./scripts/init-billing-table.sh  # first time only
./scripts/smoke.sh               # verify
```

URLs (all bound to `127.0.0.1`):

- LiteLLM API: <http://localhost:4000>
- LiteLLM admin: <http://localhost:4000/ui>
- Grafana: <http://localhost:3000>
- Prometheus: <http://localhost:9090>
- Postgres: `localhost:5433`

Authoritative routing config: [`litellm/config.yaml`](litellm/config.yaml).
The alias entries there are hand-edited; the per-provider catalog blocks are
managed by `../scripts/update-litellm-config.sh`.
