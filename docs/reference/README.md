# Reference

The "look it up" docs. These are short, factual, and meant to be skimmed — not read cover-to-cover. Update them when something concrete changes (a new machine, a new model, a new tool, a new subscription).

| File | What it covers |
|---|---|
| [machines.md](../../deploy/earth/machines.md) | The four machines I work on (earth + two WSL distros, jupiter, Mac mini) and how they reach each other. |
| [local-models.md](local-models.md) | The ollama models installed on Earth-AI: size, quant, what each one is good for. |
| [subscriptions.md](../../deploy/earth/subscriptions.md) | Paid services — plan, monthly cost, billing portal, where the API keys live. |
| [tools.md](tools.md) | Per-tool inventory: which tool is on which machine, which models it can talk to, where its config lives. |
| [routing.md](routing.md) | **The decision table** — given a task class, which tool/model do I pick? |

## Where to start

- **"Which model should I use right now?"** → [routing.md](routing.md)
- **"What's installed on this machine?"** → [tools.md](tools.md)
- **"How much am I paying for AI per month?"** → [subscriptions.md](../../deploy/earth/subscriptions.md)
- **"What can my GPU actually run?"** → [local-models.md](local-models.md)
- **"How do I reach earth from jupiter?"** → [machines.md](../../deploy/earth/machines.md#cross-machine-access)
