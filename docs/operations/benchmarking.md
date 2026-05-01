# Benchmarking Models

[`stack/scripts/benchmark-models.py`](../../stack/scripts/benchmark-models.py) measures the real-world performance of LiteLLM-proxied models against the local hardware. Run it whenever you add a new local model, change a quantization, or want a throughput baseline before deciding whether to pay for cloud inference.

## Prerequisites

- The LiteLLM proxy is running (`docker compose up -d`)
- A virtual key from the LiteLLM admin UI at `http://localhost:4000/ui`
- `nvidia-smi` in PATH (included with the NVIDIA driver — just works on Earth-AI)
- `psycopg2` Python package for the historical comparison column (`pip install psycopg2-binary` once if you want it; the script skips gracefully without it)

## Basic usage

```bash
cd ~/src/jomkz/earth-ai/stack

# Benchmark all local (ollama) chat models — the default
python3 scripts/benchmark-models.py --key sk-<your-virtual-key>

# Or set LITELLM_KEY once and drop the flag
export LITELLM_KEY=sk-<your-virtual-key>
python3 scripts/benchmark-models.py
```

The script reads `observability/litellm/config.yaml` automatically, so it picks up every local chat model currently configured — no need to list them by hand.

## Options

| Flag | Default | What it does |
|---|---|---|
| `--key KEY` | `$LITELLM_KEY` | LiteLLM virtual key |
| `--host URL` | `http://localhost:4000` | LiteLLM proxy URL |
| `--models m1,m2` | *(all local models)* | Benchmark specific models only |
| `--all` | off | Include cloud models (Anthropic, Gemini, OpenAI) |
| `--runs N` | 3 | Iterations per prompt per model |
| `--timeout S` | 120 | Per-request timeout in seconds |
| `--yes` / `-y` | off | Skip cloud-model confirmation prompt |
| `--no-vram` | off | Skip nvidia-smi VRAM readings |
| `--no-history` | off | Skip Postgres historical comparison |
| `--db-url URL` | `$DATABASE_URL` | Override Postgres connection string |

## Output

```
Benchmarking 6 model(s) [6 ollama]
  3 run(s) × 3 prompts = 9 samples per model

  deepseek...........
  gemma2.............
  qwen2.5-coder......
  ...

Model                       Provider    TTFT p50   Tok/s p50   Lat p50   Lat p95   Hist p50   Hist t/s    VRAM
────────────────────────────────────────────────────────────────────────────────────────────────────────────────
qwen2.5-coder               ollama        312 ms    47.3 t/s   3124 ms   3890 ms    2987 ms   44.1 t/s   9.1 GB
deepseek                    ollama        289 ms    43.1 t/s   3401 ms   4102 ms    3250 ms   41.7 t/s   9.2 GB
gemma2                      ollama        198 ms    61.2 t/s   2103 ms   2387 ms    2041 ms   58.9 t/s   5.7 GB
qwen2.5-coder-15b           ollama         48 ms   142.8 t/s    312 ms    389 ms     298 ms  138.4 t/s   1.1 GB
qwen2.5-coder-32b           ollama        891 ms    19.4 t/s  12043 ms  14201 ms       —          —     20.4 GB
qwen2.5-coder-32b-instruct  ollama       1203 ms    12.7 t/s  16872 ms  18340 ms       —          —     12.9 GB

Total samples: 54  (6 model(s) OK, 0 failed)
```

### Column reference

| Column | What it means |
|---|---|
| **TTFT p50** | Median time to first token across all samples. Dominated by VRAM load time on the first call, then pure inference latency on subsequent ones. |
| **Tok/s p50** | Median output token generation throughput. The primary hardware performance metric — higher is faster. |
| **Lat p50 / p95** | Median and 95th-percentile total request latency (first byte to last token). |
| **Hist p50 / Hist t/s** | 30-day historical baseline from `LiteLLM_SpendLogs`. Lets you see if the controlled benchmark matches real-traffic patterns. |
| **VRAM** | GPU memory increase after the first inference of this model. Reflects how much VRAM the model occupies when loaded. |

### What to look for

- **Tok/s** is the headline number for local hardware. A faster tok/s means less waiting for long responses and code generation.
- **TTFT** on the first call is mostly about model load time from disk into VRAM — it will be higher than subsequent calls. The p50 smooths this out across the 9 samples per model.
- **VRAM** drives whether multiple models can be in memory simultaneously. If the total VRAM footprint of the models you use daily exceeds the GPU, ollama will page in/out between calls (and TTFT spikes).
- If **Hist t/s** is lower than **Tok/s p50**, it usually means real traffic tends to ask for longer responses (more context pressure) than the short benchmark prompts.

## Selecting specific models

```bash
# Just the two models you're comparing
python3 scripts/benchmark-models.py --models qwen2.5-coder,qwen2.5-coder-32b

# More iterations for a tighter estimate
python3 scripts/benchmark-models.py --models deepseek --runs 10

# Faster run — fewer prompts is not possible, but fewer runs helps
python3 scripts/benchmark-models.py --runs 1 --no-history
```

## Including cloud models

Cloud models measure API network latency from earth, not local hardware performance. The script will prompt for confirmation before running them.

```bash
# All providers — asks before calling cloud APIs
python3 scripts/benchmark-models.py --all

# Skip the prompt (useful in scripts)
python3 scripts/benchmark-models.py --all --yes
```

Cloud models won't have a VRAM column (not applicable) and their latency is dominated by network round-trip to the provider's inference cluster, not your GPU.

## First run is slow

On the first call to any ollama model, ollama loads the weights from disk into VRAM. That load is included in the TTFT measurement for that sample. With `--runs 3`, you get one cold and two warm samples — the p50 naturally de-emphasises the cold outlier.

If you want to pre-warm a model before benchmarking (so all samples are warm):

```bash
# Send a throwaway call to load the model first
curl -s http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5-coder:14b","prompt":"hi","stream":false}' > /dev/null
python3 scripts/benchmark-models.py --models qwen2.5-coder
```

## Historical data from LiteLLM

The `Hist p50` and `Hist t/s` columns come from `LiteLLM_SpendLogs` in Postgres (last 30 days, models with ≥ 3 calls). They require the `DATABASE_URL` environment variable to be set — which it is if you run the script from the `stack/` directory with the `.env` loaded — and the `psycopg2` Python package.

If either is missing the columns are simply omitted. Install psycopg2 once if you want them:

```bash
pip install psycopg2-binary
```
