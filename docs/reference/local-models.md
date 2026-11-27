# Local Models (ollama on Earth-AI)

This is the catalog of ollama models that the workstation pulls and uses, what each one is good for, and how to change the set.

## Baseline set (pulled by `provision.sh`)

The authoritative list of models is [`provision/models.list`](../../provision/models.list). The provisioner reads it; everything else here is documentation.

| Model | Size | Params | Quant | Good for |
|---|---:|---|---|---|
| `nomic-embed-text` | 0.27 GB | 137M | F16 | Embeddings (768-dim). RAG / semantic search over local files. Don't chat with this one. |
| `qwen2.5-coder:1.5b` | 0.99 GB | 1.5B | Q4_K_M | Tab-completion / autocomplete sidecar. Fast on CPU. Pair with editor "fill-in-the-middle". |
| `qwen2.5-coder:14b` | 8.99 GB | 14.8B | Q4_K_M | **Daily-driver coder.** Default for code tasks via ollama. |
| `deepseek-r1:14b` | 8.99 GB | 14.8B | Q4_K_M | Reasoning — multi-step planning, chain-of-thought style problems. Use when the task is "think it through, then answer". |
| `gemma2:9b` | 5.44 GB | 9.2B | Q4_0 | Generalist — summarization, drafting, log triage, non-code Q&A. |

Total disk: **≈ 25 GB** for this set. Files live in `~/.ollama/models` on Earth-AI.

`deepseek-r1:14b`, `gemma2:9b` and `qwen2.5-coder:1.5b` stay until the general re-benchmark
([#29](https://github.com/terrella-project/terrella/issues/29)) picks the 2026 models that
replace them. The models an agent harness runs against, each at the context it needs, are in
[`provision/agent-models.list`](../../provision/agent-models.list).

### Adding / removing a baseline model

The list is an editable plain-text file — one model per line, `#` for comments:

```bash
cd ~/src/terrella
$EDITOR provision/models.list
bash provision/provision.sh        # pulls anything new (idempotent)

# To actually drop a model from disk, also remove it by hand:
ollama rm <model-name>

git add provision/models.list
git commit -m "Models: add foo, drop bar"
```

The provisioner never deletes models — that's deliberate, so a typo or merge can't wipe gigabytes.

## When to pick which

| Task | Pick |
|---|---|
| Generate / edit code, daily flow | `qwen2.5-coder:14b` |
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
ollama pull <model>         # add a new one ad-hoc (NOT in models.list)
ollama rm <model>           # remove from disk
df -h ~/.ollama             # check disk usage
```

For a richer dump (sizes in GB, parameter count, quant level):

```bash
curl -s http://localhost:11434/api/tags | python3 -c "
import json, sys
d = json.load(sys.stdin)
for m in sorted(d['models'], key=lambda x: x['name']):
    sz = m['size'] / 1e9
    p = m['details'].get('parameter_size', '?')
    q = m['details'].get('quantization_level', '?')
    print(f\"{m['name']:<45} {sz:>6.2f} GB  {p:<8} {q}\")
"
```

> If you pull a model ad-hoc with `ollama pull`, it will live on disk but won't be re-pulled by a fresh provision on another machine. Add it to [`provision/models.list`](../../provision/models.list) to make it part of the reproducible baseline.

## Benchmarking throughput

To measure actual tok/s, TTFT, and VRAM footprint for the installed models, run the benchmark script:

```bash
cd ~/src/terrella/stack
python3 scripts/benchmark-models.py
```

See [operations/benchmarking.md](../operations/benchmarking.md) for full usage, output reference, and how to interpret results.

## Ideas / TODO

- [ ] Add a small reasoning model like `phi-4` for fast structured output.
