# Local model refresh, November 2026 (#29)

This records how the 2025 set of local models was replaced: what was measured, the results, and
what was chosen from them. The tool and its task sets are described in
[benchmarking.md](benchmarking.md#evaluating-models-per-role). The roles the chosen models now
serve are listed in [local models](../reference/local-models.md).

## Setup

- **Machine:** earth, an RTX 5080 (16 GB) with driver 620.70.06 and ollama 0.40.18. Every model
  ran alone on the card, through ollama's native API.
- **Task sets:** the files in `stack/eval/` as merged. Each results file records the task sets'
  SHA-256, the harness's SHA-256, and each model's digest.
- **Decoding:** temperature 0 with seed 29, unless a row says otherwise. Context was 4k for
  `fim`, 16k for `reason`, `general` and `code`, and 64k for `agent` (the `-64k` variants).
- **Token budget per reply:** `fim` 64, `general` 3,072, `code` 6,144, `reason` 12,288.
- **Speed:** ollama's own `eval_count` over `eval_duration`, for replies of 8 tokens or more.
  The wait is the median request time with the model already loaded.
- **GPU memory:** the rise in `nvidia-smi`'s figure once the model had loaded.

Scores are a count of tasks passed. The task sets are small (5 to 40 items), so a difference of
one or two tasks is not a finding. Treat the rankings as coarse.

## Tab completion (`fim`): 40 holes, 3 passes each

| Model | Holes right | Line-exact | Wait p50 / p95 | GPU | Notes |
|---|---:|---:|---|---:|---|
| **qwen2.5-coder:3b** | **21** | 15 | 106 / 248 ms | 2.3 GB | chosen |
| qwen2.5-coder:7b | 17 | 12 | 389 / 451 ms | 4.8 GB | |
| qwen2.5-coder:1.5b | 16 | 10 | 51 / 156 ms | 1.4 GB | the 2025 model |
| granite-code:3b | 13 | 9 | 278 / 327 ms | 3.6 GB | |
| starcoder2:3b | 8 | 6 | 210 / 233 ms | 2.1 GB | |
| codegemma:2b-code | 0 | 0 | — | 2.0 GB | broken on this ollama, see below |

- **No 2026 chat model can fill a hole.** ollama answers "does not support insert" for lfm3,
  mimo-v2.6, ornith, ornith-1.5, bonsai-2 and nemotron-3.5-bolt. The library's templates show the
  same for gemma4, gpt-oss, devstral and granite4. Only the code-model families take a suffix.
- **The scores are low across the board.** Several holes need details of this repository that
  no model could guess, such as an exact header name. Every model faced the same holes, so the
  ranking holds. The absolute numbers do not mean much.
- **codegemma:2b-code is broken here, not bad.** Sent the raw FIM prompt with no stop words, it
  echoes its own `<|fim_…|>` tokens as text. This ollama build does not read them as special
  tokens.
- **Two runs gave the same scores.** Within a run, 2 to 7 of the 80 repeat completions changed
  their graded lines. That is ollama reusing its prompt cache on a repeat.

## Summaries and log triage (`general`): 8 tasks, every reply read by hand

| Model | Screen | Wait p50 | GPU | Read by hand |
|---|---:|---|---:|---|
| deepseek-r1:14b | 8/8 | 5.8 s | 11.6 GB | accurate; over-advises ("stop the server", "upgrade the GPU") |
| bonsai-2:27b | 8/8 | 5.9 s | 9.4 GB | the most precise, but advised `ollama rm` (which deletes a model) to unload one; called a per-day row "a single call" |
| **nemotron-3.5-bolt:e4b** | **7/8** | **1.1 s** | 8.1 GB | chosen; terse and correct; missed the root cause in the offload task |
| mimo-v2.6:9b | 7/8 | 1.8 s | 6.9 GB | the best prose; one reply ran out of budget while thinking; one commit message had no body |
| gemma4:12b | 6/8 | 3.1 s | 9.4 GB | |
| ornith-1.5:9b | 6/8 | 3.9 s | 7.1 GB | |
| lfm3:1.7b | 5/8 | 4.8 s | 1.6 GB | two replies ran out of budget |
| gemma2:9b | 4/8 | 0.6 s | 7.9 GB | the 2025 model: wrong total ($13.90), called a running gateway "partially up" |
| gpt-oss:20b | 4/8 | 2.1 s | 12.7 GB | spills off the GPU at 16k |

The screen checks each reply for the facts it requires and the claims it forbids. Reading the
replies found two things the screen had missed:

- a forbidden pattern had failed nemotron for listing "anthropic" as an example provider; it
  was narrowed, and the saved replies were graded again;
- three errors of the kind no list foresees: the `ollama rm` advice, the invented "single
  call", and the missing commit body.

## Coding (`code`): 20 functions with hidden tests

| Model | Thinking | Passed | Cut off | Wait p50 | GPU | Notes |
|---|---|---:|---:|---|---:|---|
| **gemma4:12b** | **off** | **15** | 0 | **2.2 s** | 9.5 GB | chosen |
| gpt-oss:20b | default | 16 | 4 | 10.5 s | 12.8 GB | spills off the GPU |
| gpt-oss:20b | low | 15 | 0 | 4.5 s | 12.2 GB | spills off the GPU |
| ornith-1.5:9b | default | 10 | 10 | 40.8 s | 7.1 GB | |
| ornith-1.5:9b | off | 10 | 0 | 2.3 s | 6.9 GB | |
| devstral:24b | — | 10 | 0 | 18.1 s | 12.7 GB | spills: 13 tokens/s |
| qwen2.5-coder:14b | — | 9 | 0 | 2.5 s | 11.7 GB | the 2025 model; stays, pinned by name |
| gemma4:12b | default | 5 | 15 | 27.0 s | 9.5 GB | |
| mimo-v2.6:9b | default | 5 | 3 | 2.9 s | 7.1 GB | |
| mimo-v2.6:9b | off | 2 | 0 | 2.3 s | 7.2 GB | real bugs: units walked smallest-first, etc. |

- **Thinking cost the thinking models their scores.** A reply that is cut off has spent its
  whole 6,144-token budget thinking and written no code. With thinking off, gemma4 went from 5
  to 15.
- **For tab-speed coding, thinking off is the setting that counts.** The gateway's
  `local/code` entry sends `reasoning_effort: none`, which LiteLLM passes on to ollama as
  `think=false`.

## Embeddings (`embed`): 30 questions over this repository's docs

The corpus is 220 sections (264 chunks) at commit `e450b7a`. A question scores when the section
that answers it comes back first (recall@1) or in the top five (recall@5).

| Model | Prefixes | recall@1 | recall@5 | MRR | Docs/s | GPU |
|---|---|---:|---:|---:|---:|---:|
| **embeddinggemma-2** | **documented** | 0.60 | **0.97** | 0.74 | 12 | 1.9 GB |
| embeddinggemma-2 | none | 0.50 | 0.87 | 0.65 | 29 | 1.8 GB |
| nomic-embed-text-v2-moe | documented | 0.60 | 0.90 | 0.72 | 24 | 0.8 GB |
| qwen3-embedding | instruction | 0.63 | 0.83 | 0.73 | 24 | 5.8 GB |
| nomic-embed-text | documented | 0.53 | 0.80 | 0.66 | 23 | 0.7 GB |

- **One question is 0.033.** The recall@1 spread of 0.50 to 0.63 is four questions, which is not
  a separation. The recall@5 gap is five questions.
- **The prefixes matter for embeddinggemma-2.** Without them it scores 0.87 at recall@5, which
  still beats every row except nomic v2's. Continue does not send prefixes, so its index gets
  the plain figure.
- **Open WebUI is not affected.** It uses its own built-in embedder (all-MiniLM-L6-v2), and it
  had no indexed documents.

## Agent tool loop (`agent`): 5 tasks at 64k context

Every model passed 5/5 except one:

| Model | Result |
|---|---|
| gpt-oss:20b | 4/5: grepped for a file name instead of reading the file; spills at 64k |
| bonsai-2:27b | 5/5, but it spilled in one of two runs: it sits at the card's edge at 64k |

The screen says whether a model can drive tools at all; it does not rank them. `local/agent`
stays on ornith-1.5:9b, which the real-task benchmark of 2026-11-26 chose (#29, first comment).

## Reasoning (`reason`): 30 problems with one checkable answer

The problems cover arithmetic, logic, dates and units, code tracing, and planning, six of
each. Each one has a single answer, and a program in the task set computes it. Where three or
more models gave the same wrong answer, the key was checked again by hand. It held each time:
the shared wrong answers were the traps the problems were built around.

The "own" column uses each model's published sampling settings instead of temperature 0. It
was added after gemma4, at temperature 0, found the right answer and then kept re-checking it
until its budget ran out: 30,783 characters of thinking and no answer. Open WebUI and Continue
use the model's own settings anyway, so that column is closer to real use.

| Model | Greedy | Own | Cut off (greedy / own) | Wait p50 (own) | All 30 (own) | GPU |
|---|---:|---:|---|---|---|---:|
| gpt-oss:20b | 24 | **29** | 4 / 1 | 8.2 s | 6.9 min | 12.8 GB; spilled in 4 of 5 runs |
| bonsai-2:27b | 28 | — | 2 / — | — | — | 9.5 GB; the own-sampling run was stopped by an out-of-memory event |
| ornith-1.5:9b | 26 | 25 | 3 / 2 | 12.6 s | 10.8 min | 7.1 GB |
| **nemotron-3.5-bolt:e4b** | **25** | **25** | 0 / 0 | **3.3 s** | **2.2 min** | 8.1 GB; chosen |
| gemma4:12b | 2 | 24 | 28 / 6 | 31.7 s | 16.9 min | 9.4 GB |
| deepseek-r1:14b | 22 | — | 4 / — | 34.0 s (greedy) | 28.3 min (greedy) | 11.6 GB; the 2025 model |
| mimo-v2.6:9b | 17 | — | 9 / — | 16.5 s (greedy) | 18.0 min (greedy) | 7.1 GB |

- **nemotron serves `local/reason` as well as `local/general`.** Its score is the same under both
  kinds of sampling, it was never cut off, and it is about ten times faster than the larger
  thinkers. One model for both roles also means fewer model swaps on the card.
- **gpt-oss scores best, but it does not fit the card reliably.** At 16k context it spilled into
  system memory in four of five runs. It would also evict almost everything else.
- **The remaining own-sampling runs were stopped on purpose.** Loading bonsai-2 pushed earth out
  of memory: the four HTG runner VMs hold 25–30 GB, and loading a model takes far more host
  memory than its file size, so ollama peaked at 33 GB. A check for free RAM before each load
  (`--min-free-gb`) did not prevent it. Run a long evaluation only with the machine otherwise
  quiet.

## What the measurements taught the tool

Each of these produced a believable but wrong number before it was caught, and each is now a
guard in `eval-local-models.py`:

- **Speed from a one-token reply read as a million tokens a second.** Speed now counts only
  replies of 8 tokens or more.
- **An empty reply cut off by the token limit was counted as "empty".** It is now "truncated",
  which is a warning.
- **A score over graded replies showed 16/16 for a model that passed 16 of 20.** The
  denominator is now the task count.
- **A correct `5 069` (with a narrow no-break space) failed an `5,?069` match.** Thin and
  no-break spaces between digits are now dropped before grading.
- **A model that checked a file existed before reading it was failed for using the "wrong
  tool".** The agent loop now allows tools that can help, and counts those calls.
- **A FIM repeat that changed only the text after the hole was flagged as nondeterministic.**
  Only the graded lines count now.
- **At temperature 0, gemma4 found the right answer and then re-checked it until its budget
  ran out.** `--sampling model` runs a model with its own sampling settings instead.

## Removed

The 2025 models replaced here (`qwen2.5-coder:1.5b`, `gemma2:9b`, `deepseek-r1:14b`), the losing candidates, and
`nomic-embed-text`, once Continue has re-indexed, are removed from earth by hand after this
change merges. `provision/sync-models.sh` never removes a model. `qwen2.5-coder:14b` stays.
