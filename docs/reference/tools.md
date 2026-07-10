# Tool Inventory

What's installed where, and how each tool reaches which model. Update when something changes.

## Per-machine matrix

earth runs Fedora 44 with a single environment (the WSL dev/services split retired at M0).

| Tool | earth (Fedora 44) | jupiter (laptop) | Mac mini |
|---|---|---|---|
| VS Code + GitHub Copilot | ✅ | ✅ via Remote-WSL | _TODO_ |
| GitHub Copilot CLI (`gh copilot`) | _TODO_ | _TODO_ | _TODO_ |
| Claude Code CLI | ✅ | ✅ | _TODO_ |
| OpenCode | _TODO_ | ✅ | _TODO_ |
| ollama (server) | ✅ user service, port 11434 | n/a (uses earth's) | _TODO_ |
| MCP servers (GitHub MCP quadlet) | ✅ port 8765 (bearer auth) | _TODO_ | _TODO_ |
| LiteLLM proxy | ✅ quadlet, port 4000 | client via Tailscale | (client only) |
| Grafana | ✅ quadlet, port 3000 | browser via Tailscale | (browser only) |
| Prometheus | ✅ quadlet, port 9090 | browser via Tailscale | (browser only) |
| Tailscale | ⏳ pending (#4 apply) | ✅ | _TODO_ |
| podman (rootless quadlets) | ✅ 5.8.3 | n/a (not needed) | _TODO_ |
| `gh` (GitHub CLI) | ✅ 2.96.0 | ✅ | _TODO_ |

## Tool → models routing

### GitHub Copilot (VS Code)

- Picker in chat. Models: Claude Sonnet, GPT-4.1/4o, Gemini 2.5 Pro, "Copilot" (default).
- Cost: counts against my Copilot Team quota — not metered per call here; budget tracked monthly via `log-billing.sh`.
- Custom instructions live in `.github/copilot-instructions.md` per repo and `AGENTS.md`/`CLAUDE.md` in this workspace.

### Claude Code CLI

- Models: Claude Sonnet, Claude Opus.
- Cost: subscription (Pro/Max), tracked monthly via `log-billing.sh`.
- Reads workspace context from `CLAUDE.md` files automatically.

### OpenCode

- Multi-model TUI. Configured via `opencode.json` in the workspace.
- Can route to Anthropic, Gemini, OpenAI, ollama. _TODO: confirm current config_.

### ollama (direct)

- Endpoint: `http://localhost:11434` on earth or `http://earth:11434` over Tailscale.
  Containers on the `terrella` network use `http://host.containers.internal:11434`.
- OpenAI-compatible: `/v1/chat/completions`, `/v1/embeddings`.
- Models in [local-models.md](local-models.md).

### LiteLLM proxy (the routing point)

- Endpoint: `http://localhost:4000` on earth or `http://earth:4000` over Tailscale.
- OpenAI-compatible — every tool that takes `OPENAI_BASE_URL` + `OPENAI_API_KEY` can be pointed at it.
- Authoritative routing config source: [`../../stack/observability/litellm/config.yaml`](../../stack/observability/litellm/config.yaml), rendered to `~/.config/terrella/litellm/config.yaml` by `stack/quadlet/install.sh`. Lists all backend models (anthropic/*, gemini/*, openai/*, ollama/*), per-key spend caps, model aliases.
- Use it when I want a request to **show up in Grafana**. Skip it when I'm using a tool that has its own UI/billing (Copilot, Claude Code).

## MCP servers

Configured in `mcp.json` at the root of this workspace:

- **github** — `ghcr.io/github/github-mcp-server` as the `terrella-github-mcp` quadlet
  (streamable HTTP on port 8765, per-request bearer auth with the PAT since v1.x).

Per the existing in-repo `runner/agent_runner.py`, MCP tools are NOT available inside CI runs of that runner — only `run_command` is. MCP only works in interactive tools (Claude Code, Copilot, OpenCode).

## Where each tool stores its config

| Tool | Config path |
|---|---|
| VS Code | `~/.vscode-server/` (Remote-WSL host); user settings sync via GitHub login |
| Copilot instructions | per-repo `.github/copilot-instructions.md`, workspace `AGENTS.md` |
| Claude Code | per-repo `CLAUDE.md`, workspace `CLAUDE.md`, `.claude/settings.local.json` |
| OpenCode | workspace `opencode.json` |
| `agent_runner.py` | per-agent `.agent.md` files in `.github/agents/` |
| LiteLLM | `stack/observability/litellm/config.yaml` (source) → `~/.config/terrella/litellm/config.yaml` (rendered) |
| ollama | `~/.ollama/` + `stack/quadlet/ollama.service` |
| MCP | workspace `mcp.json` |
| Secrets | `stack/.env` (mode 600) → split into `~/.config/terrella/env.d/*.env` by `stack/quadlet/install.sh` |
