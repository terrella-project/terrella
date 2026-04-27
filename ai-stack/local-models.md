# Local Models (ollama on Earth-AI)

Snapshot taken 2026-04-27. Source: `curl http://localhost:11434/api/tags` from Ubuntu-24.04 WSL on earth.

Refresh with:

```bash
curl -s http://localhost:11434/api/tags \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f\"{m['name']:<45} {m['size']/1e9:>6.2f} GB  {m['details'].get('parameter_size','?'):<8} {m['details'].get('quantization_level','?')}\") for m in sorted(d['models'], key=lambda x: x['name'])]"
```

## Installed

| Model | Size | Params | Quant | Good for |
|---|---:|---|---|---|
| `qwen2.5-coder:32b` | 19.85 GB | 32.8B | Q4_K_M | **Top local coder.** Single-file refactors, code generation, code review where I want decent quality without paying the API. Slowest. |
| `qwen2.5-coder:32b-instruct-q2_K` | 12.31 GB | 32.8B | Q2_K | Same model, more aggressive quantization — fits in less VRAM, somewhat lower quality. Use if Q4_K_M is too slow. |
| `qwen2.5-coder:14b` | 8.99 GB | 14.8B | Q4_K_M | **Daily-driver coder.** Faster than 32b, still very capable. Default for code tasks via ollama. |
| `qwen2.5-coder:1.5b` | 0.99 GB | 1.5B | Q4_K_M | Tab-completion / autocomplete sidecar. Fast on CPU. Pair with editor "fill-in-the-middle". |
| `deepseek-r1:14b` | 8.99 GB | 14.8B | Q4_K_M | Reasoning — multi-step planning, chain-of-thought style problems. Use when the task is "think it through, then answer". |
| `gemma2:9b` | 5.44 GB | 9.2B | Q4_0 | Generalist — summarization, drafting, log triage, non-code Q&A. |
| `nomic-embed-text:latest` | 0.27 GB | 137M | F16 | Embeddings (768-dim). For RAG / semantic search over local files. Don't chat with this one. |

## When to pick which

| Task | Pick |
|---|---|
| Generate / edit code, daily flow | `qwen2.5-coder:14b` |
| Generate / edit code, want best quality and willing to wait | `qwen2.5-coder:32b` |
| Inline tab-completion, low latency required | `qwen2.5-coder:1.5b` |
| "Reason through this and explain" | `deepseek-r1:14b` |
| Summarize logs / long output / non-code prose | `gemma2:9b` |
| Build a vector index over source files / docs | `nomic-embed-text` |

## Running them

From any tool, ollama is OpenAI-compatible at `http://localhost:11434/v1`:

```bash
# Quick chat
ollama run qwen2.5-coder:14b "Review this diff..."

# OpenAI-style API
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:14b","messages":[{"role":"user","content":"hello"}]}'
```

Through LiteLLM (preferred — gives logging + Grafana visibility):

```bash
export OPENAI_BASE_URL=http://localhost:4000
export OPENAI_API_KEY=<my-virtual-key>
# Now any OpenAI-style client routed at LiteLLM with model name "ollama/qwen2.5-coder:14b" hits ollama
```

## Model housekeeping

```bash
# On Earth-AI (where ollama runs)
ollama list                 # what's installed
ollama pull <model>         # add a new one
ollama rm <model>           # remove
df -h ~/.ollama             # check disk usage
```

Disk: model files live in `~/.ollama/models` on Earth-AI. Current set is ≈57 GB on disk.

## Ideas / TODO

- [ ] Try `qwen2.5-coder:32b-instruct-q4_K_M` (different quant) and compare with `qwen2.5-coder:32b`.
- [ ] Add a small reasoning model like `phi-4` for fast structured output.
- [ ] Decide whether to keep both `32b` and `32b-instruct-q2_K` once I've measured throughput.
