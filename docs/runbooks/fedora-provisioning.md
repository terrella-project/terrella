# Runbook — provisioning a Fedora host for the terrella stack

Host-level prerequisites for the M0 quadlet stack on Fedora
([#4](https://github.com/terrella-project/terrella/issues/4); ADR-0002/ADR-0004). Everything
here is scripted in [`provision/fedora/bootstrap.sh`](../../provision/fedora/bootstrap.sh) —
idempotent, safe to re-run after kernel/driver updates, `--check` for detect-only:

```bash
provision/fedora/bootstrap.sh          # apply (steps sudo where needed)
provision/fedora/bootstrap.sh --check  # detect-only, changes nothing
```

The script doubles as the behavioral spec for the M1 provisioning framework's fedora/dnf
adapter. The legacy WSL provisioner (`provision/provision.sh`) is untouched and retired
with M0.

## What it sets up

| Step | Detail |
|---|---|
| RPM Fusion free + nonfree | source of `akmod-nvidia` |
| NVIDIA driver | `akmod-nvidia` with **open kernel modules** (`%_with_kmod_nvidia_open 1`) — Blackwell GPUs (RTX 5080) only work with the open flavor; verified via `modinfo -F license nvidia` → `Dual MIT/GPL` |
| Secure Boot | detect-only: if SB is on and no akmods MOK is enrolled, prints the `kmodgenca` + `mokutil --import` steps. earth currently runs with SB disabled |
| nvidia-container-toolkit | NVIDIA's dnf repo; provides `nvidia-ctk` |
| CDI spec | `nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml` — how rootless podman containers get the GPU (`--device nvidia.com/gpu=all`) |
| CDI regen on updates | the spec pins driver paths and goes stale on every kernel/driver update. Prefer the toolkit's `nvidia-cdi-refresh.path` (≥ 1.17.7); fallback: [`terrella-cdi-regen.service`](../../provision/fedora/terrella-cdi-regen.service), a boot-time oneshot ordered `After=akmods.service` |
| podman + linger | rootless runtime; `loginctl enable-linger` so the user stack starts at boot and survives logout |
| Tailscale | dnf repo + `tailscaled`; join manually with `sudo tailscale up --ssh` as node **earth** (the old `earth-ai` node retires per #78) |
| Acceptance tests | rootless GPU (`podman run --device nvidia.com/gpu=all … nvidia-smi`) and an SELinux `:Z` bind-mount probe |

## Notes

- **No M0 container needs the GPU** — ollama runs on the host (#12). The CDI/rootless-GPU
  test de-risks M1+; its failure is not an M0 blocker. Escape hatch per ADR-0002: run a
  GPU-needing unit rootful from `/etc/containers/systemd/`.
- firewalld zone configuration (loopback + tailnet exposure only) is tracked separately
  (#10) and documented in
  [cross-machine-access.md](../operations/cross-machine-access.md).
- earth state at first run (2026-07-09): rpmfusion, akmod-nvidia 595.80 (open modules
  loaded), podman 5.8.3, and linger were already in place from the OS install; the script
  detected and skipped them.
