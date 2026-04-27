# Tool Inventory

What's installed where, and how each tool reaches which model. Update when something changes.

## Per-machine matrix

| Tool | Ubuntu-24.04 (earth) | Earth-AI (earth) | laptop | Mac mini |
|---|---|---|---|---|
| VS Code + GitHub Copilot | ✅ via Remote-WSL | n/a | _TODO_ | _TODO_ |
| GitHub Copilot CLI (`gh copilot`) | _TODO_ | _TODO_ | _TODO_ | _TODO_ |
| Claude Code CLI | _TODO_ | _TODO_ | _TODO_ | _TODO_ |
| OpenCode | _TODO_ | _TODO_ | _TODO_ | _TODO_ |
| ollama (server) | n/a | ✅ port 11434 | _TODO_ | _TODO_ |
| TrackPro `runner/agent_runner.py` | ✅ in `~/src/trackpro` | n/a | _TODO_ | _TODO_ |
| MCP servers (GitHub MCP via Docker) | ✅ from `mcp.json` | _TODO_ | _TODO_ | _TODO_ |
| LiteLLM proxy | (client only) | ✅ port 4000 | (client only) | (client only) |
| Grafana | (browser only) | ✅ port 3000 | (browser only) | (browser only) |
| Prometheus | (browser only) | ✅ port 9090 | (browser only) | (browser only) |
| Tailscale | ❌ | _TODO_ | _TODO_ | _TODO_ |
| Docker + Compose v2 | ✅ 29.4.1 | _TODO_ | _TODO_ | _TODO_ |
| `gh` (GitHub CLI) | ✅ | _TODO_ | _TODO_ | _TODO_ |

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

### TrackPro `runner/agent_runner.py`

- Default `LLM_PROVIDER=gemini`, model `gemini-2.5-flash`. Override with `--provider openai` / `--model`.
- Used by GitHub Actions workflow `.github/workflows/ai_self_heal.yml`.
- Future: add `ollama` provider + `OPENAI_BASE_URL` override so it can target LiteLLM. Tracked in TrackPro meta-repo issue (see [routing.md](routing.md#future-automation)).

### ollama (direct)

- Endpoint: `http://localhost:11434` (from any WSL distro on earth) or `http://earth-ai:11434` over Tailscale.
- OpenAI-compatible: `/v1/chat/completions`, `/v1/embeddings`.
- Models in [local-models.md](local-models.md).

### LiteLLM proxy (the routing point)

- Endpoint: `http://localhost:4000` on Earth-AI (and on this Ubuntu-24.04 WSL via mirrored networking) or `http://earth-ai:4000` over Tailscale.
- OpenAI-compatible — every tool that takes `OPENAI_BASE_URL` + `OPENAI_API_KEY` can be pointed at it.
- Authoritative routing config: [`../../stack/litellm/config.yaml`](../../stack/litellm/config.yaml) on Earth-AI. Lists all backend models (anthropic/*, gemini/*, ollama/*), per-key spend caps, model aliases.
- Use it when I want a request to **show up in Grafana**. Skip it when I'm using a tool that has its own UI/billing (Copilot, Claude Code).

## MCP servers

Configured in `mcp.json` at the root of this workspace:

- **github** — `ghcr.io/github/github-mcp-server` via Docker. Uses `GITHUB_PERSONAL_ACCESS_TOKEN` env var.

Per the existing in-repo `runner/agent_runner.py`, MCP tools are NOT available inside CI runs of that runner — only `run_command` is. MCP only works in interactive tools (Claude Code, Copilot, OpenCode).

## Where each tool stores its config

| Tool | Config path |
|---|---|
| VS Code | `~/.vscode-server/` (Remote-WSL host); user settings sync via GitHub login |
| Copilot instructions | per-repo `.github/copilot-instructions.md`, workspace `AGENTS.md` |
| Claude Code | per-repo `CLAUDE.md`, workspace `CLAUDE.md`, `.claude/settings.local.json` |
| OpenCode | workspace `opencode.json` |
| `agent_runner.py` | per-agent `.agent.md` files in `.github/agents/` |
| LiteLLM | `~/src/jomkz/earth-ai/stack/litellm/config.yaml` |
| ollama | `~/.ollama/` (on Earth-AI) |
| MCP | workspace `mcp.json` |
| Secrets | `~/.config/trackpro/secrets` (sourced by `~/.bashrc`) |
