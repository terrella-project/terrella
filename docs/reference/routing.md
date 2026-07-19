# Routing — Manual Heuristics

This is the **contract** for which tool to pick for which task. Manual today; automation tracked separately (see [Future automation](#future-automation)).

Rule of thumb: **prefer local first when quality is good enough; reserve paid for hard problems.**

## Decision table

| Task class | Tool | Model | Why |
|---|---|---|---|
| **Default in-editor coding flow** | Copilot | Claude Sonnet (or "Copilot" default) | Already in VS Code, instant context, flat-rate. |
| **Tab-completion / inline FIM** | Copilot, or local via Continue.dev pointing at ollama | `qwen2.5-coder:1.5b` | Latency-sensitive; 1.5B is fast enough on CPU. |
| **Multi-file refactor with agent loop** | Claude Code | Sonnet (Opus for hard) | Best agent UX, large effective context, safe defaults. |
| **One-shot greenfield design / architecture spike** | Gemini API (free tier or paid) | `gemini-2.5-pro` | Largest context window, cheapest for big-context tasks. |
| **Code review of a diff (single PR)** | Copilot inline review, or Claude Code if subtle | varies | Lowest friction. |
| **Bulk doc generation / mass edits** | Gemini API | `gemini-2.5-flash` | Cheap, fast, doesn't burn Claude/Copilot quota. |
| **CI / automation scripts** | custom scripts via LiteLLM | `gemini-2.5-flash` | Cheap; calls log to Grafana automatically. |
| **Quick local Q&A / "what does this regex do?"** | ollama via terminal | `qwen2.5-coder:14b` or `gemma2:9b` | No round-trip cost; private. |
| **Single-file edit / log triage / commit-message draft** | ollama via LiteLLM | `qwen2.5-coder:14b` | Cheap, private, shows up in Grafana for tracking. |
| **Long reasoning / "think then answer"** | Local first | `deepseek-r1:14b`; escalate to Claude Opus if it stalls | Try free first. |
| **Embeddings for RAG / semantic search** | ollama | `nomic-embed-text` | Free, fast, never leaves machine. |
| **Anything sensitive / secrets / private data** | ollama only | any local | Stays on earth, never leaves the network. |
| **Off-network on jupiter or mercury** | Paid services direct | varies | If Tailscale isn't worth the hop, pay for it. |
| **Off-network but want to use earth's models** | Tailscale → LiteLLM | any | Works the same as on earth, just slower. |

## Model naming across nodes (gateway aliases)

Adopted now so nothing has to be renamed when a second serving node (**neptune**) comes
online — see [ADR-0010](../adr/ADR-0010-neptune-future-primary-node.md). Today every local
model is served by earth, so the routed group and the pinned name resolve to the same
backend; the convention just reserves the shape.

- **`local/<model>`** — a routed model *group*. Clients and automation use this by default;
  the gateway picks a backend (and, once neptune exists, prefers the always-on node and
  fails over when earth is gaming). This is what the decision table's "local" rows map to.
- **`earth/<model>`, `neptune/<model>`** — pinned single-node names, for benchmarking,
  debugging, and "I specifically want that GPU."
- **Cloud names** (`claude-*`, `gemini-*`, `gpt-*`) are unchanged.

Failover is connection-error cooldown, **not** background health checks — background checks
bill real completions ([#96](https://github.com/terrella-project/terrella/issues/96)).
Liveness is surfaced instead by a non-billable `terrella_node_up{node}` probe in
observability, so "earth is gaming" shows in Grafana without any spend.

## Escalation ladder (when the cheap thing isn't good enough)

For coding:
1. `qwen2.5-coder:14b` (local) →
2. `qwen2.5-coder:32b` (local, slower) →
3. Copilot (Claude Sonnet) →
4. Claude Code (Opus) →
5. Anthropic API (Opus) for one-off heavy lifting

For reasoning:
1. `deepseek-r1:14b` (local) →
2. Claude Sonnet (Copilot or Claude Code) →
3. Claude Opus

For "I just want a fast cheap answer":
1. `gemma2:9b` (local) →
2. Gemini Flash via API

## Cost tracking implications

When I deliberately route a task through LiteLLM (instead of using Copilot/Claude Code's UI), the call shows up in Grafana. So:

- Use **Copilot / Claude Code** when in flow and don't care about per-task accounting — flat-rate captured monthly.
- Route through **LiteLLM** when I want to know exactly what a workflow costs (e.g. measuring the cost of a nightly automation job).

## What NOT to route through LiteLLM

- VS Code Copilot traffic (would violate ToS to intercept)
- Claude Code traffic (same)
- Anything in the browser that doesn't take an `OPENAI_BASE_URL`

LiteLLM is for **API clients I control**: scripts, OpenCode, Continue.dev, anything that lets me set a base URL.
