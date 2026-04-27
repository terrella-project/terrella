# `provision/`

One-shot installer for the Earth-AI WSL distro plus the list of ollama models it pulls.

| File | Purpose |
|---|---|
| [`provision.sh`](provision.sh) | Idempotent installer: apt deps, systemd-in-WSL, ollama (with CORS / network overrides), Docker, Aider, baseline ollama models. |
| [`models.list`](models.list) | The list of ollama models the script pulls. One per line; comments allowed. |

## Run it

```bash
cd ~/src/jomkz/earth-ai
bash provision/provision.sh
```

Then `wsl --shutdown` from PowerShell and reopen the terminal so the systemd-in-WSL change takes effect.

Re-running is safe — every step is idempotent (`apt install` is a no-op for already-installed packages, `ollama pull` is a no-op for already-present models, etc.).

## Add or change a model

1. Edit [`models.list`](models.list).
2. Re-run `bash provision/provision.sh` (or just `ollama pull <model>` if that's all you want).
3. To **remove** a model, delete its line in `models.list` **and** run `ollama rm <model>` by hand. The provisioner never deletes models — that's deliberate, so a typo can't wipe gigabytes.

The format is "first whitespace-separated field is the model name; everything after `#` is a comment":

```
qwen2.5-coder:14b   # 8.99 GB   daily-driver coder
```

→ Full guide on what each model is for: [`docs/reference/local-models.md`](../docs/reference/local-models.md).
