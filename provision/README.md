# `provision/`

Machine provisioner and model manager for the Earth-AI WSL distro. These two scripts are independent — run them separately.

| File | Purpose |
|---|---|
| [`provision.sh`](provision.sh) | Idempotent machine setup: apt deps, systemd-in-WSL, ollama (with CORS / network overrides), Docker, Aider. Does **not** pull models. |
| [`sync-models.sh`](sync-models.sh) | Reads [`models.list`](models.list) and pulls each model. Safe to re-run — `ollama pull` is a no-op for already-present models. |
| [`models.list`](models.list) | The model catalog. One model per line; inline comments allowed. Edit this file to add or remove models. |

## Provision the machine

```bash
cd ~/src/jomkz/earth-ai
bash provision/provision.sh
```

Then `wsl --shutdown` from PowerShell and reopen the terminal so the systemd-in-WSL change takes effect.

Re-running is safe — every step is idempotent (`apt install` is a no-op for already-installed packages, etc.).

## Pull / update models

```bash
cd ~/src/jomkz/earth-ai
bash provision/sync-models.sh
```

Re-running is safe — `ollama pull` is a no-op for models that are already up to date.

## Add or change a model

1. Edit [`models.list`](models.list).
2. Re-run `bash provision/sync-models.sh`.
3. To **remove** a model, delete its line in `models.list` **and** run `ollama rm <model>` by hand. Neither script ever deletes models — that's deliberate, so a typo can't wipe gigabytes.

The format is "first whitespace-separated field is the model name; everything after `#` is a comment":

```
qwen2.5-coder:14b   # 8.99 GB   daily-driver coder
```

→ Full guide on what each model is for: [`docs/reference/local-models.md`](../docs/reference/local-models.md).
