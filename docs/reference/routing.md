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
| **Off-network on jupiter or Mac mini** | Paid services direct | varies | If Tailscale isn't worth the hop, pay for it. |
| **Off-network but want to use earth's models** | Tailscale → LiteLLM | any | Works the same as on earth, just slower. |

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
