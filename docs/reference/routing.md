# Routing — Manual Heuristics

This is the **contract** for which tool to pick for which task. Manual today; automation is roadmap phase M5, benchmark-informed routing (see [ROADMAP.md](../../ROADMAP.md#phases)).

Rule of thumb: **prefer local first when quality is good enough; reserve paid for hard problems.**

## Decision table

| Task class | Tool | Model | Why |
|---|---|---|---|
| **Default in-editor coding flow** | Copilot | Claude Sonnet (or "Copilot" default) | Already in VS Code, instant context, flat-rate. |
| **Tab-completion / inline FIM** | Copilot, or local via Continue.dev through LiteLLM | `local/fim` | Latency-sensitive: about 100 ms a completion on the 5080. |
| **Multi-file refactor with agent loop** | Claude Code | Sonnet (Opus for hard) | Best agent UX, large effective context, safe defaults. |
| **One-shot greenfield design / architecture spike** | Gemini API (free tier or paid) | `gemini-2.5-pro` | Largest context window, cheapest for big-context tasks. |
| **Code review of a diff (single PR)** | Copilot inline review, or Claude Code if subtle | varies | Lowest friction. |
| **Bulk doc generation / mass edits** | Gemini API | `gemini-2.5-flash` | Cheap, fast, doesn't burn Claude/Copilot quota. |
| **CI / automation scripts** | custom scripts via LiteLLM | `gemini-2.5-flash` | Cheap; calls log to Grafana automatically. |
| **Quick local Q&A / "what does this regex do?"** | ollama via LiteLLM | `local/general` | No round-trip cost; private; about a second an answer. |
| **Single-file edit** | ollama via LiteLLM | `local/code` | Cheap, private, shows up in Grafana for tracking. |
| **Log triage / summaries / commit-message draft** | ollama via LiteLLM | `local/general` | Read a local summary before acting on it: local models still invent the odd detail. |
| **Long reasoning / "think then answer"** | Local first | `local/reason`; escalate to Claude Opus if it stalls | Try free first. |
| **Embeddings for RAG / semantic search** | ollama via LiteLLM | `local/embed` | Free, never leaves the machine. |
| **Anything sensitive / secrets / private data** | ollama only | any local | Stays on earth, never leaves the network. |
| **Off-network on jupiter or mercury** | Paid services direct | varies | If Tailscale isn't worth the hop, pay for it. |
| **Off-network but want to use earth's models** | Tailscale → LiteLLM | any | Works the same as on earth, just slower. |

## Model naming across nodes (gateway aliases)

Adopted now so nothing has to be renamed when a second serving node (**neptune**) comes
online — see [ADR-0010](../adr/ADR-0010-neptune-future-primary-node.md). Today every `local/`
role is served by earth. neptune, up without its GPUs, serves one pinned name,
`neptune/llama3.2:3b`, to prove the route (#99). The convention reserves the shape for when
roles can fail over between the two.

- **`local/<role>`** — a routed *role*: `local/fim`, `local/general`, `local/reason`,
  `local/code`, `local/embed`, `local/agent`. Clients and automation use these by default;
  the gateway decides which model serves each role (chosen from measurements, see
  [local models](local-models.md)) and, once neptune exists, which backend (preferring the
  always-on node and failing over when earth is gaming). This is what the decision table's
  "local" rows map to.
- **`ollama/<model>`** — one catalog model by name, for a client whose results depend on the
  exact model (fighters-legacy pins `qwen2.5-coder:14b`, for one).
- **`earth/<model>`, `neptune/<model>`** — pinned single-node names, for benchmarking,
  debugging, and "I specifically want that GPU."
- **Cloud names** (`claude-*`, `gemini-*`, `gpt-*`) are unchanged.
- **`local/agent`**: the local model an agent harness asks for. It is served through ollama's
  own Anthropic-format endpoint with a 64k context, so a harness that speaks that format (the
  Claude Agent SDK, for one) can run its tool loop against it. Which model serves it is one line
  in the gateway config, so agents keep the name when the model changes. A gateway key whose
  model list holds only this name cannot reach a paid model.

Failover is connection-error cooldown, **not** background health checks — background checks
bill real completions ([#96](https://github.com/terrella-project/terrella/issues/96)).
Liveness is surfaced instead by a non-billable `terrella_node_up{node}` probe in
observability, so "earth is gaming" shows in Grafana without any spend.

## Escalation ladder (when the cheap thing isn't good enough)

For coding:

1. `local/code` (local) →
2. Copilot (Claude Sonnet) →
3. Claude Code (Opus) →
4. Anthropic API (Opus) for one-off heavy lifting

For reasoning:

1. `local/reason` (local) →
2. Claude Sonnet (Copilot or Claude Code) →
3. Claude Opus

For "I just want a fast cheap answer":

1. `local/general` (local) →
2. Gemini Flash via API

## Cost tracking implications

When I deliberately route a task through LiteLLM (instead of using Copilot/Claude Code's UI), the call shows up in Grafana. So:

- Use **Copilot / Claude Code** when in flow and don't care about per-task accounting — flat-rate captured monthly.
- Route through **LiteLLM** when I want to know exactly what a workflow costs (e.g. measuring the cost of a nightly automation job).
- **Unattended agents** run under their own gateway keys in the `agents` team. The team's budget follows the monthly API credit and resets with it. Two panels on the "AI Stack Overview" dashboard show the team's spend this cycle against a straight line to its budget, read from the team record and the ledger: one is the line over the cycle, the other gives the figures now. The runner, its schedules and its end-of-cycle backlog are outside this repository.

## What NOT to route through LiteLLM

- VS Code Copilot traffic (would violate ToS to intercept)
- Claude Code traffic (same)
- Anything in the browser that doesn't take an `OPENAI_BASE_URL`

LiteLLM is for **API clients I control**: scripts, OpenCode, Continue.dev, anything that lets me set a base URL.
