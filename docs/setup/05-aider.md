# Aider (Agentic Coding CLI)

Aider is a terminal-based pair-programmer. You point it at a directory of source code and chat with it; it edits the files and commits as it goes. We run it against ollama so it costs nothing.

## 5.1 Install in a virtualenv

```bash
mkdir -p ~/tools/aider
python3 -m venv ~/tools/aider/venv
~/tools/aider/venv/bin/pip install --upgrade pip
~/tools/aider/venv/bin/pip install aider-chat
```

Why a venv? It keeps `aider-chat`'s dependencies away from your system Python. The next upgrade is `~/tools/aider/venv/bin/pip install -U aider-chat`.

## 5.2 (Optional) Add a wrapper to your `PATH`

```bash
mkdir -p ~/.local/bin
ln -sf ~/tools/aider/venv/bin/aider ~/.local/bin/aider
# Make sure ~/.local/bin is in PATH (it usually is on Ubuntu).
```

## 5.3 Run it against ollama

```bash
export OLLAMA_API_BASE=http://localhost:11434
cd /path/to/some/project
aider --model ollama/qwen2.5-coder:14b
```

That puts you at the Aider prompt. Type a request like:

```
> add a unit test for parse_date()
```

Aider will diff its proposed edit, ask you to confirm, and then commit on success.

> **Want spend tracking?** Point Aider at LiteLLM instead of straight at ollama once the [full stack](06-observability-stack.md) is up — see [reference/tools.md](../reference/tools.md). Calls then show up in Grafana.

## 5.4 Picking a model

| Use case | `--model` flag |
|---|---|
| Daily flow on the 5080 | `ollama/qwen2.5-coder:14b` |
| Hard refactor, willing to wait | `ollama/qwen2.5-coder:32b` |
| Chain-of-thought / "think it through" tasks | `ollama/deepseek-r1:14b` |
| Final review with cloud quality | `claude-3-5-sonnet-latest` (via LiteLLM) |

Full table: → [reference/routing.md](../reference/routing.md).

## ✅ Verification

```bash
aider --version           # prints something like "aider 0.x.y"
which aider               # ~/.local/bin/aider or ~/tools/aider/venv/bin/aider
```

→ on to [full stack setup](06-observability-stack.md) to add the proxy + dashboard.
