# AI Observability Stack

Self-hosted single pane of glass for AI usage and cost across Anthropic, Gemini, OpenAI, and ollama. Plus a manual entry path for flat-rate subscriptions (Copilot, Claude Code).

Lives in the [`earth-ai`](../README.md) repo alongside the Open WebUI compose, the WSL provisioning scripts, and the [`ai-stack/`](../ai-stack/README.md) reference notes.

> **Intended host:** Earth-AI WSL (same distro that runs ollama). Both the LiteLLM proxy here and ollama listen on the host's loopback; LiteLLM uses `network_mode: host` to reach ollama.

## Components

| Service | Port | Purpose |
|---|---|---|
| `litellm` | 4000 | OpenAI-compatible proxy → Anthropic / Gemini / OpenAI / ollama. Logs every call. |
| `postgres` | 5433 (host) | Backing store for LiteLLM + the `monthly_costs` manual-entry table. |
| `prometheus` | 9090 | Scrapes LiteLLM `/metrics`. |
| `grafana` | 3000 | Dashboards — combines LiteLLM per-call spend + manual subscription rows. |

ollama runs **outside** this stack (it's already up on Earth-AI on port 11434). LiteLLM connects to it via the host network.

## Quick start

Run from this directory on Earth-AI WSL.

```bash
# 1. Ensure secrets are loaded into the shell
#    (these come from ~/.config/trackpro/secrets, which is sourced by ~/.bashrc)
echo "$ANTHROPIC_API_KEY" | head -c 6   # sanity check — should print "sk-ant"
echo "$GEMINI_API_KEY"   | head -c 6
echo "$OPENAI_API_KEY"   | head -c 6 || true   # optional

# 2. Generate strong secrets the first time
./scripts/generate-env.sh   # writes .env (gitignored, chmod 600)

# 3. Bring the stack up
docker compose up -d

# 4. First-time DB setup for the manual-billing table
./scripts/init-billing-table.sh
```

## URLs (from the host running the stack)

| | URL | Auth |
|---|---|---|
| LiteLLM | http://localhost:4000 | Virtual API keys (see `litellm/config.yaml`) |
| LiteLLM admin | http://localhost:4000/ui | `LITELLM_MASTER_KEY` from `.env` |
| Grafana | http://localhost:3000 | admin / `GRAFANA_ADMIN_PASSWORD` from `.env` |
| Prometheus | http://localhost:9090 | none (bind to localhost only) |
| Postgres | localhost:5433 | `litellm` / `POSTGRES_PASSWORD` from `.env`; DB `litellm` |

## Cross-machine access (Tailscale)

After Tailscale is installed on Earth-AI:

```bash
tailscale serve --bg --tcp 4000 tcp://localhost:4000   # LiteLLM
tailscale serve --bg --tcp 3000 tcp://localhost:3000   # Grafana
# ollama is its own thing — tailscale serve --bg --tcp 11434 tcp://localhost:11434
```

Then from laptop / Mac mini:

```bash
export OPENAI_BASE_URL=http://earth-ai:4000
export OPENAI_API_KEY=<my virtual key from litellm/config.yaml>
```

## Files

```
ai-observability/
├── README.md                          (this file)
├── docker-compose.yml
├── .env.example                       (template; copy to .env)
├── .gitignore
├── litellm/
│   └── config.yaml                    (model list, virtual keys, routing)
├── prometheus/
│   └── prometheus.yml
├── grafana/
│   ├── provisioning/datasources/datasources.yml
│   └── provisioning/dashboards/dashboards.yml
├── sql/
│   └── monthly_costs.sql              (DDL for manual subscription tracking)
└── scripts/
    ├── generate-env.sh                (one-time: write .env with random secrets)
    ├── init-billing-table.sh          (one-time: create monthly_costs)
    ├── log-billing.sh                 (interactive: insert a monthly subscription cost row)
    └── smoke.sh                       (probe LiteLLM end-to-end)
```

## Manual subscription billing

Copilot and Claude Code don't expose per-call telemetry. Capture them after each billing cycle:

```bash
./scripts/log-billing.sh
# Month (YYYY-MM): 2026-04
# Vendor (copilot|claude-code|anthropic|gemini|other): copilot
# Amount USD: 19.00
# Notes (optional): Team plan, 1 seat
```

Grafana has a "Total spend" panel that sums LiteLLM call costs (per-vendor) with the rows in `monthly_costs` so all four lines show up together.

## Verifying

```bash
./scripts/smoke.sh                      # routes a tiny chat to ollama via LiteLLM
# Then open Grafana → "AI Stack Overview" dashboard and confirm the call appears.
```

## Security posture

- `.env` is `chmod 600`, gitignored, never committed.
- Postgres is bound to `127.0.0.1` only.
- LiteLLM and Grafana ports are only exposed on `127.0.0.1`; cross-machine access is via Tailscale, not a public listener.
- LiteLLM requires a virtual key for every request (`master_key` only used to manage keys).
- Backend API keys live in `~/.config/trackpro/secrets` and are passed in by docker-compose env interpolation, not baked into images.
