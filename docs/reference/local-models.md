# Local Models (ollama on earth)

This page lists the ollama models earth serves, the gateway role each one fills, and how to
change the set.

## Roles, not models

Clients ask the gateway for a **role** (`local/<role>`), never for a model. The gateway
config ([`stack/observability/litellm/config.yaml`](../../stack/observability/litellm/config.yaml))
decides which model serves each role. A model can therefore be replaced without touching any
client, as long as the measurements say the new one does the job better. The models were
chosen from the measurements in [model-refresh-2026-11.md](../operations/model-refresh-2026-11.md).

| Role | What it is for | Model | GPU memory | Typical wait |
|---|---|---|---:|---|
| `local/fim` | tab completion: fill the hole between the code before and after the cursor | `qwen2.5-coder:3b` | 2.3 GB | ~0.1 s |
| `local/general` | summaries, log triage, drafting, quick questions | `nemotron-3.5-bolt:e4b` | 8.1 GB | ~1 s |
| `local/reason` | "think it through": problems with one right answer | `nemotron-3.5-bolt:e4b` | 8.1 GB | ~4 s |
| `local/code` | write and edit code (thinking off) | `gemma4:12b` | 9.5 GB | ~2 s |
| `local/embed` | embeddings for retrieval and semantic search | `embeddinggemma-2` | 1.9 GB | — |
| `local/agent` | an agent harness's tool loop, 64k context | `ornith-1.5:9b-64k` | 8.5 GB | — |

GPU memory is the rise in `nvidia-smi`'s figure on the RTX 5080 with the model loaded at the
role's context; the card holds 16 GB, so ollama swaps models in as roles are called. The wait
is the median from the evaluation.

`qwen2.5-coder:14b` is also kept, pinned by name (`ollama/qwen2.5-coder-14b`): it is the local
default that fighters-legacy measured its AI features against.

### Things worth knowing

- **Only code models can fill a hole.** No 2026 chat model in the ollama library accepts the
  `suffix` a tab completion sends; ollama answers "does not support insert". `local/fim` stays
  on the qwen2.5-coder family for that reason.
- **`local/fim` goes through ollama's OpenAI-compatible `/v1/completions`.** LiteLLM's `ollama/`
  route puts the `suffix` where ollama's `/api/generate` ignores it, so a tab completion through
  the gateway used to see only the code before the cursor.
- **`local/code` runs with thinking off.** With thinking on, gemma4 spent its whole budget
  thinking on most coding tasks and wrote no code; with it off it scored best of the models
  that fit the card. The gateway entry sets `reasoning_effort: none`, which LiteLLM sends to
  ollama as `think=false`. A client calling ollama directly does not get that.
- **Changing `local/embed` invalidates every index built with the old model.** Continue
  rebuilds its codebase index when the model changes. Open WebUI uses its own built-in embedder
  and is not affected.
- **Read a local summary before acting on it.** The best local summarisers still invented the
  odd detail in the evaluation (one advised `ollama rm`, which deletes a model, to unload one).

## The catalog

The authoritative list is [`provision/models.list`](../../provision/models.list);
[`provision/sync-models.sh`](../../provision/sync-models.sh) pulls it. Agent models, each with
the context it runs at, are in [`provision/agent-models.list`](../../provision/agent-models.list),
and `sync-models.sh` creates the `<model>-<N>k` variant for each. Everything else here is
documentation.

### Changing a model

```bash
cd ~/src/terrella

# 1. Measure the candidate against the role's current model first
python3 stack/scripts/eval-local-models.py <role> --models <current>,<candidate>

# 2. Change the catalog and the gateway role
$EDITOR provision/models.list
$EDITOR stack/observability/litellm/config.yaml       # the local/<role> entry
bash provision/sync-models.sh                         # pulls anything new (idempotent)
(cd stack && ./scripts/update-litellm-config.sh ollama)  # the ollama/<model> catalog block
systemctl --user restart terrella-litellm

# 3. Remove the old model from disk by hand
ollama rm <old-model>
```

The provisioner never deletes models, so a typo or a merge cannot wipe gigabytes. See
[benchmarking.md](../operations/benchmarking.md) for the evaluation tool.

## Calling them

Through LiteLLM (preferred: keys, the spend ledger and Grafana see every call):

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" \
  -d '{"model":"local/general","messages":[{"role":"user","content":"Summarise: ..."}]}'
```

Straight at ollama (no ledger, and `local/code`'s thinking setting does not apply):

```bash
ollama run qwen2.5-coder:14b "Review this diff..."
```

## Model housekeeping

```bash
ollama list                 # what's installed
ollama ps                   # what's loaded, and how much of it is on the GPU
ollama rm <model-name>      # remove from disk
df -h ~/.ollama             # disk use
```

> A model pulled ad hoc with `ollama pull` lives on disk but is not part of the catalog: a fresh
> provision on another machine will not pull it, and the gateway does not serve it. Add it to
> [`provision/models.list`](../../provision/models.list) to make it part of the set.
