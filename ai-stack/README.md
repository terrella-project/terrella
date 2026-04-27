# AI Stack — Personal Reference

Scope: my development AI tooling across machines and providers. NOT committed to any TrackPro repo.

## Files

| File | Contents |
|---|---|
| [machines.md](machines.md) | earth (Windows host + 2 WSL distros), laptop, Mac mini |
| [subscriptions.md](subscriptions.md) | Copilot, Claude, Anthropic, Gemini — tier, cost, limits |
| [local-models.md](local-models.md) | ollama models on Earth-AI, sizes, intended use |
| [tools.md](tools.md) | Per-tool / per-machine inventory |
| [routing.md](routing.md) | **Decision table — task class → which tool to use** |

## Decision-at-a-glance

| Situation | Use |
|---|---|
| Coding inside VS Code, normal flow | **GitHub Copilot** (this is the default) |
| Multi-step refactor, large repo context, agent loops | **Claude Code** (Sonnet/Opus) |
| Greenfield design / architecture / cost-sensitive bulk work | **Gemini API** (cheap, large context) |
| Quick local Q&A, single-file edits, log/diff triage, embeddings | **ollama on earth** (qwen2.5-coder, deepseek-r1, nomic-embed) |
| Anything sensitive that should not leave my network | **ollama on earth** |
| TrackPro CI agents (`agent_runner.py`) | **Gemini** (current default) |

Full rules in [routing.md](routing.md).

## Cross-machine quickstart

| From | To use ollama | To use LiteLLM proxy |
|---|---|---|
| Ubuntu-24.04 WSL on earth | `http://localhost:11434` | `http://localhost:4000` |
| Earth-AI WSL on earth | `http://localhost:11434` | `http://localhost:4000` |
| Laptop / Mac mini | `http://earth-ai.<tailnet>:11434` (Tailscale) | `http://earth-ai.<tailnet>:4000` (Tailscale) |

See [machines.md](machines.md#cross-machine-access) for the Tailscale setup.

## Observability

LiteLLM + Postgres + Prometheus + Grafana, hosted on Earth-AI WSL. Configuration lives in [`../ai-observability/`](../ai-observability/README.md) (sibling directory in this repo). Dashboard: `http://localhost:3000` (or via Tailscale from other machines).

Subscription costs (Copilot, Claude Code) are not metered per-request — they are entered manually each month with `../ai-observability/scripts/log-billing.sh` and unioned into the Grafana "Total spend" panel.
