# `stack/`

Docker-compose stack: **LiteLLM proxy + Postgres + Prometheus + Grafana**.

This directory contains only the runtime artifacts (compose file, configs, scripts, SQL). All documentation lives under [`../docs/`](../docs/):

| You want to… | Read |
|---|---|
| Install and bring this stack up | [`../docs/setup/06-observability-stack.md`](../docs/setup/06-observability-stack.md) |
| Log monthly Copilot / Claude bills | [`../docs/operations/manual-billing.md`](../docs/operations/manual-billing.md) |
| Reach this stack from another machine | [`../docs/operations/cross-machine-access.md`](../docs/operations/cross-machine-access.md) |
| Diagnose a broken stack | [`../docs/operations/troubleshooting.md`](../docs/operations/troubleshooting.md) |

Quick start (assumes you've read the setup doc):

```bash
cd ~/src/jomkz/earth-ai/stack
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
