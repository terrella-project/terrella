# Benchmarking Models

[`stack/scripts/benchmark-models.py`](../../stack/scripts/benchmark-models.py) measures the real-world performance of LiteLLM-proxied models against the local hardware. Run it whenever you add a new local model, change a quantization, or want a throughput baseline before deciding whether to pay for cloud inference.

## Prerequisites

- The LiteLLM proxy is running (`systemctl --user start terrella.target`)
- A virtual key from the LiteLLM admin UI at `http://localhost:4000/ui`
- `nvidia-smi` in PATH (included with the NVIDIA driver)
- `psycopg2` Python package for persistence and the historical comparison column
  (`pip install --user psycopg2-binary` once; the script skips gracefully without it —
  **but then results are not recorded**, which is how the WSL era ended up with no
  stored baseline)
- The `benchmark_results` table exists (first time:
  `podman exec -i terrella-postgres psql -U litellm -d litellm < sql/benchmark_results.sql`)
- `DATABASE_URL` pointing at the published Postgres port:
  `postgresql://litellm:<password>@127.0.0.1:5433/litellm`

## Basic usage

```bash
cd ~/src/terrella/stack

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
| `--no-write` | off | Skip persisting results to Postgres |
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

If you want to pre-warm a model before benchmarking (so all samples are warm), use `--no-write` with a single throwaway run first — the model stays loaded in VRAM between the two invocations:

```bash
# Warm-up pass (discarded), then the real benchmark
python3 scripts/benchmark-models.py --models qwen2.5-coder --runs 1 --no-write
python3 scripts/benchmark-models.py --models qwen2.5-coder
```

This works for multiple models too — the warm-up pass loads each one in sequence, and Ollama keeps them resident until its keep-alive timeout (default 5 minutes), so run both passes back-to-back.

## Fedora baseline (2026-07-09)

First recorded baseline, run against the freshly migrated quadlet stack (M0, #13) —
RTX 5080 16 GB, native Fedora driver 595.80, ollama 0.31.2 as a user service. Persisted
to `benchmark_results`; earlier WSL-era runs were never persisted (no `psycopg2`), so
the *Hist* columns from the restored `LiteLLM_SpendLogs` are the only WSL-era comparator.

| Model | TTFT p50 | Tok/s p50 | Lat p50 | VRAM |
|---|---:|---:|---:|---:|
| qwen2.5-coder-15b (1.5b FIM) | 209 ms | 455.3 t/s | 420 ms | 1.4 GB |
| gemma2 (9b) | 419 ms | 133.7 t/s | 988 ms | 9.7 GB |
| qwen2.5-coder (14b) | 421 ms | 98.3 t/s | 993 ms | 0.9 GB* |
| qwen2.5-coder-32b-instruct (q2_K) | 516 ms | 66.0 t/s | 1534 ms | 14.4 GB |
| qwen2.5-coder-32b | 3143 ms | 8.2 t/s | 9688 ms | (spills to RAM) |
| deepseek (r1:14b) | 1383 ms | 0.0 t/s† | 1383 ms | 9.1 GB |

\* VRAM delta under-reads when the model was already resident from a previous row.
† `deepseek-r1` spends the token budget inside its `<think>` block and returns empty
visible content at low `max_tokens`, so the script counts 0 output tokens — a
known measurement artifact to fix with the M2 model refresh (#29), not an infra failure.

Takeaways: the q2_K 32b variant earns its place (66 t/s inside 16 GB); the full 32b
confirms its "overflows VRAM" warning; the 14b daily driver at ~98 t/s comfortably beats
the WSL-era feel.

## Running on the same machine as Ollama

The benchmark script runs on the same machine that serves LiteLLM and Ollama. That's convenient but introduces a few measurement effects worth knowing about.

**CPU contention.** The script itself is lightweight, but if a model runs on CPU (no GPU or partial VRAM offload), the benchmark process competes for the same cores during inference. Tok/s numbers will be slightly lower than they would be on an idle machine.

**TTFT includes model load time.** When Ollama hasn't loaded a model yet, the first request blocks until the weights are in VRAM. That load time is included in the TTFT sample. With the default `--runs 3` you get one cold sample and two warm ones — the p50 de-emphasises the outlier, but it doesn't disappear. Use the `--no-write` pre-warm two-pass approach (see [First run is slow](#first-run-is-slow)) if you want all samples to be warm.

**VRAM delta is approximate.** The script snapshots VRAM before and after the full model run (all prompts × runs). If Ollama evicts a previously loaded model during the run, or hasn't fully unloaded it before starting the next model, the delta will be off. Treat the VRAM column as an order-of-magnitude guide rather than a precise measurement.

**Single-client throughput only.** Results reflect one request at a time from one client. Real usage with multiple concurrent users will produce lower tok/s and higher latency — the benchmark numbers are most useful for comparing models against each other, not for predicting production capacity.

**(WSL platform only) memory pressure.** WSL2 balloons its memory allocation as models load. If the total model footprint approaches the Windows host's WSL memory limit, Windows will start paging, which shows up as wide p50→p95 latency spreads. Native Fedora has no such ballooning — one of the reasons M0 migrated.

## Historical data from LiteLLM

The `Hist p50` and `Hist t/s` columns come from `LiteLLM_SpendLogs` in Postgres (last 30 days, models with ≥ 3 calls). They require the `DATABASE_URL` environment variable to be set — which it is if you run the script from the `stack/` directory with the `.env` loaded — and the `psycopg2` Python package.

If either is missing the columns are simply omitted. Install psycopg2 once if you want them:

```bash
pip install psycopg2-binary
```
