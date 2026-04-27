# Phase 6 — Observability Stack (LiteLLM + Postgres + Prometheus + Grafana)

The observability stack is a single docker-compose project that gives you:

- A **single OpenAI-compatible endpoint** (LiteLLM) that fans out to Anthropic, Gemini, OpenAI, and ollama based on the model name in each request.
- **Per-call cost logging** to Postgres.
- **Prometheus** scraping LiteLLM's `/metrics`.
- A **Grafana dashboard** ("AI Stack Overview") that combines per-call costs with a manually-entered table of monthly subscription costs (for Copilot, Claude Code) so all four lines of spend appear in one chart.

This phase is **not** in `provision.sh` because it has secrets to wire up.

## 6.1 Components

| Service | Port (host) | Purpose |
|---|---|---|
| `litellm` | 4000 | OpenAI-compatible proxy → Anthropic / Gemini / OpenAI / ollama. Logs every call. |
| `postgres` | 5433 | Backing store for LiteLLM + the `monthly_costs` manual-entry table. |
| `prometheus` | 9090 | Scrapes LiteLLM `/metrics`. |
| `grafana` | 3000 | Dashboards. |

> ollama runs **outside** this stack — it's already up from Phase 3. LiteLLM connects to it via `network_mode: host`.

## 6.2 Prerequisites

You should have:

- Phases 1–4 complete.
- Cloud API keys exported into your shell. The convention on this machine is to put them in `~/.config/trackpro/secrets`, which `~/.bashrc` sources at login. They look like:

  ```bash
  export ANTHROPIC_API_KEY=sk-ant-...
  export GEMINI_API_KEY=...
  export OPENAI_API_KEY=sk-...   # optional
  ```

  Sanity-check before bringing the stack up:

  ```bash
  echo "$ANTHROPIC_API_KEY" | head -c 6   # → "sk-ant"
  echo "$GEMINI_API_KEY"   | head -c 6
  echo "$OPENAI_API_KEY"   | head -c 6 || true
  ```

## 6.3 Bring it up

Run from the `stack/` directory:

```bash
cd ~/src/jomkz/earth-ai/stack

# 1. First-time only: generate strong random secrets into .env
./scripts/generate-env.sh   # writes .env (gitignored, chmod 600)

# 2. Start the stack
docker compose up -d

# 3. First-time only: create the manual-billing table
./scripts/init-billing-table.sh
```

`generate-env.sh` populates `.env` with a Postgres password, a Grafana admin password, and the LiteLLM master key. The file is `chmod 600` and gitignored — it never leaves the machine.

## 6.4 URLs (from the host running the stack)

| | URL | Auth |
|---|---|---|
| LiteLLM API | <http://localhost:4000> | Virtual API keys (see `litellm/config.yaml`) |
| LiteLLM admin UI | <http://localhost:4000/ui> | `LITELLM_MASTER_KEY` from `.env` |
| Grafana | <http://localhost:3000> | `admin` / `GRAFANA_ADMIN_PASSWORD` from `.env` |
| Prometheus | <http://localhost:9090> | none (bound to localhost) |
| Postgres | localhost:5433 | `litellm` / `POSTGRES_PASSWORD` from `.env`; DB `litellm` |

## 6.5 Files in `stack/`

```
stack/
├── docker-compose.yml
├── .env.example                       # template; copy to .env (or run generate-env.sh)
├── .gitignore
├── litellm/
│   └── config.yaml                    # model list, virtual keys, routing rules
├── prometheus/
│   └── prometheus.yml
├── grafana/
│   └── provisioning/
│       ├── datasources/datasources.yml
│       └── dashboards/dashboards.yml  # auto-loads JSON from grafana/provisioning/dashboards/json/
├── sql/
│   └── monthly_costs.sql              # DDL for manual subscription table
└── scripts/
    ├── generate-env.sh                # one-time: write .env with random secrets
    ├── init-billing-table.sh          # one-time: create monthly_costs
    ├── log-billing.sh                 # interactive: insert a monthly subscription cost row
    └── smoke.sh                       # probe LiteLLM end-to-end
```

The authoritative routing table — which model alias maps to which provider, which keys exist, per-key spend caps — lives in [`../../stack/litellm/config.yaml`](../../stack/litellm/config.yaml).

## 6.6 Verify end-to-end

```bash
cd ~/src/jomkz/earth-ai/stack
./scripts/smoke.sh
```

The script sends a tiny chat to ollama **via LiteLLM**. Then open Grafana → "AI Stack Overview" and confirm the call appears in the recent-calls panel.

## 6.7 Use it from a client

Any OpenAI-style client can be pointed at LiteLLM:

```bash
export OPENAI_BASE_URL=http://localhost:4000
export OPENAI_API_KEY=<my-virtual-key-from-litellm/config.yaml>

# Now this hits ollama, but the call is logged to Grafana:
curl $OPENAI_BASE_URL/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/qwen2.5-coder:14b",
    "messages": [{"role":"user","content":"hello"}]
  }'
```

Switch `model` to `claude-3-5-sonnet-latest` or `gemini-2.5-flash` (or whatever aliases you defined in `litellm/config.yaml`) to fan out to a different provider — same client code, same dashboard.

## 6.8 Manual subscription billing

Copilot Team and Claude Code Pro/Max are flat-rate, so they don't have per-call telemetry. After each billing cycle:

```bash
./scripts/log-billing.sh
# Month (YYYY-MM): 2026-04
# Vendor (copilot|claude-code|anthropic|gemini|other): copilot
# Amount USD: 19.00
# Notes (optional): Team plan, 1 seat
```

This inserts a row into Postgres's `monthly_costs` table. The Grafana "Total spend" panel sums these rows alongside per-call LiteLLM costs so all spend lines up in one chart.

→ Full procedure (and how to query / fix typos) in [operations/manual-billing.md](../operations/manual-billing.md).

## 6.9 Security posture

- `.env` is `chmod 600`, gitignored, never committed.
- Postgres is bound to `127.0.0.1` only.
- LiteLLM and Grafana ports listen on `127.0.0.1` only — cross-machine access is via Tailscale, not a public listener.
- LiteLLM requires a **virtual key** for every request; the `master_key` is only used to manage keys, never to make calls.
- Backend API keys live in `~/.config/trackpro/secrets` and are passed in by `docker-compose` env interpolation, **not baked into images**.

## ✅ Verification

```bash
docker compose ps                                 # all four containers "running"
curl -s http://localhost:4000/health/liveness      # → {"status":"healthy"}
./scripts/smoke.sh                                 # ends with "OK"
```

Setup complete! 🎉 Move on to:

- [reference/routing.md](../reference/routing.md) — which model to pick for which task.
- [operations/cross-machine-access.md](../operations/cross-machine-access.md) — using earth from a laptop / Mac mini.
- [operations/maintenance.md](../operations/maintenance.md) — backups, gaming toggle, day-2 ops.
