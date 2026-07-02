# ADR-0003 — Keep LiteLLM behind a gateway-driver boundary

**Date:** 2026-07-01 · **Status:** Accepted

## Context

LiteLLM is the stack's multi-provider gateway and per-call cost ledger. Mid-2026 comparisons
still rank it the default for self-hosted use (100+ providers, virtual keys, budgets, ollama
support, Open WebUI integration), but credible alternatives exist: TensorZero (Rust;
built-in inference→evals→routing optimization loop), Bifrost (Go; raw throughput), archgw
(prompt-aware routing). Meanwhile our dashboards and scripts read `LiteLLM_SpendLogs`
directly — a schema coupling that would make any future swap expensive.

## Decision

- **Keep LiteLLM** as the gateway for now.
- **Isolate it**: the `terrella` gateway driver renders LiteLLM's config from `terrella.yaml`;
  all consumers (Grafana, spend reports, the routing advisor) query **`terrella_spend` /
  `terrella_requests` SQL views**, never LiteLLM tables directly (M2). A gateway swap then
  means a new driver + new view definitions — nothing else moves.
- Run a **time-boxed M3 spike** on alternatives. Disqualifying criterion: a per-request cost
  ledger queryable from Postgres/OTel with fidelity ≥ `LiteLLM_SpendLogs`. The spike must
  specifically evaluate **TensorZero as a potential substrate for M5** (its optimization
  loop is the same thesis as our benchmark-informed routing), framing M5 as "build the
  advisor on LiteLLM data" vs. "adopt TensorZero's loop". Bifrost is a performance play
  irrelevant at personal QPS.

## Consequences

- Until the M2 views exist, nothing new may be built against LiteLLM's schema.
- The M3 spike output is an ADR (keep or migrate), not necessarily a migration.
- Virtual keys and Open WebUI integration are lock-ins the spike must price in.
