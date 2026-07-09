#!/usr/bin/env bash
# terrella — Fedora workstation bootstrap (M0).
#
# Idempotent detect → apply → verify for the host-level prerequisites of the
# quadlet stack: NVIDIA open kernel modules, nvidia-container-toolkit + CDI,
# podman, user lingering, and Tailscale. Run as the login user; individual
# steps use sudo. Safe to re-run after kernel/driver updates.
#
# This script is the behavioral spec for the M1 provisioning framework's
# fedora/dnf adapter (ADR-0004); keep steps small and independently checkable.
# The legacy WSL provisioner lives at provision/provision.sh and is untouched.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_ONLY="${1:-}"

pass() { echo "  ✔ $*"; }
todo() { echo "  ✚ $*"; }

step() { echo; echo "▶ $*"; }

# ── 1. RPM Fusion (akmod-nvidia lives in nonfree) ───────────────────────────
step "rpmfusion free + nonfree"
if rpm -q rpmfusion-free-release rpmfusion-nonfree-release &>/dev/null; then
    pass "already enabled"
else
    todo "enabling rpmfusion"
    [[ $CHECK_ONLY == --check ]] || sudo dnf install -y \
        "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm" \
        "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm"
fi

# ── 2. NVIDIA driver — OPEN kernel modules (required for Blackwell/RTX 5080) ─
step "akmod-nvidia (open kernel modules)"
if ! rpm -q akmod-nvidia &>/dev/null; then
    todo "installing akmod-nvidia with open modules forced"
    if [[ $CHECK_ONLY != --check ]]; then
        echo '%_with_kmod_nvidia_open 1' | sudo tee /etc/rpm/macros.nvidia-kmod >/dev/null
        sudo dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda
        echo "  ⚠ reboot (or wait for akmods) before the driver is usable; re-run afterwards"
    fi
elif [[ "$(modinfo -F license nvidia 2>/dev/null)" == "Dual MIT/GPL" ]]; then
    pass "installed, open-module flavor loaded ($(modinfo -F version nvidia 2>/dev/null || echo '?'))"
else
    echo "  ✖ akmod-nvidia present but the loaded module is NOT the open flavor."
    echo "    Blackwell GPUs require open modules:"
    echo "      echo '%_with_kmod_nvidia_open 1' | sudo tee /etc/rpm/macros.nvidia-kmod"
    echo "      sudo akmods --rebuild --force && reboot"
    exit 1
fi

# ── 3. Secure Boot: akmods modules must be MOK-signed when SB is on ─────────
step "secure boot / MOK"
SB_STATE="$(mokutil --sb-state 2>/dev/null || echo unknown)"
if [[ $SB_STATE == *enabled* ]]; then
    if mokutil --list-enrolled 2>/dev/null | grep -qi akmods; then
        pass "Secure Boot on, akmods MOK enrolled"
    else
        todo "Secure Boot is ON but no akmods MOK is enrolled — modules will not load."
        echo "    sudo kmodgenca -a && sudo mokutil --import /etc/pki/akmods/certs/public_key.der"
        echo "    then reboot and complete MOK enrollment in the firmware prompt"
    fi
else
    pass "Secure Boot disabled ($SB_STATE) — no MOK enrollment needed (revisit if re-enabled)"
fi

# ── 4. nvidia-container-toolkit + CDI spec ──────────────────────────────────
step "nvidia-container-toolkit"
if rpm -q nvidia-container-toolkit &>/dev/null; then
    pass "installed ($(rpm -q --qf '%{VERSION}' nvidia-container-toolkit))"
else
    todo "adding NVIDIA repo + installing nvidia-container-toolkit"
    if [[ $CHECK_ONLY != --check ]]; then
        curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
            | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo >/dev/null
        sudo dnf install -y nvidia-container-toolkit
    fi
fi

step "CDI spec (/etc/cdi/nvidia.yaml)"
if [[ -s /etc/cdi/nvidia.yaml ]]; then
    pass "present ($(sudo nvidia-ctk cdi list 2>/dev/null | grep -c '^nvidia.com' || echo '?') device(s))"
else
    todo "generating CDI spec"
    [[ $CHECK_ONLY == --check ]] || sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
fi

# CDI goes stale after kernel/driver updates. Toolkit ≥1.17.7 ships a refresh
# unit pair; enable it, or fall back to our boot-time oneshot ordered after akmods.
step "CDI regeneration on driver updates"
if systemctl list-unit-files nvidia-cdi-refresh.path &>/dev/null \
   && systemctl list-unit-files nvidia-cdi-refresh.path | grep -q nvidia-cdi-refresh; then
    if systemctl is-enabled nvidia-cdi-refresh.path &>/dev/null; then
        pass "toolkit's nvidia-cdi-refresh.path enabled"
    else
        todo "enabling nvidia-cdi-refresh.service + .path"
        [[ $CHECK_ONLY == --check ]] || sudo systemctl enable --now nvidia-cdi-refresh.path nvidia-cdi-refresh.service 2>/dev/null || true
    fi
else
    if [[ -f /etc/systemd/system/terrella-cdi-regen.service ]]; then
        pass "fallback terrella-cdi-regen.service installed"
    else
        todo "toolkit ships no refresh unit — installing fallback terrella-cdi-regen.service"
        if [[ $CHECK_ONLY != --check ]]; then
            sudo install -m 644 "$SCRIPT_DIR/terrella-cdi-regen.service" /etc/systemd/system/
            sudo systemctl daemon-reload
            sudo systemctl enable terrella-cdi-regen.service
        fi
    fi
fi

# ── 5. podman + user lingering (rootless stack survives logout / starts at boot)
step "podman"
if command -v podman &>/dev/null; then
    pass "podman $(podman --version | awk '{print $3}')"
else
    todo "installing podman"
    [[ $CHECK_ONLY == --check ]] || sudo dnf install -y podman
fi

step "linger for $USER"
if [[ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" == "yes" ]]; then
    pass "linger enabled"
else
    todo "enabling linger"
    [[ $CHECK_ONLY == --check ]] || sudo loginctl enable-linger "$USER"
fi

# ── 6. Tailscale (tailnet is the only remote access path — see ADR-0002/#10) ─
step "tailscale"
if command -v tailscale &>/dev/null; then
    pass "installed ($(tailscale version 2>/dev/null | head -1))"
    tailscale status &>/dev/null && pass "logged in" \
        || todo "not logged in — run: sudo tailscale up --ssh (node name: earth)"
else
    todo "adding tailscale repo + installing"
    if [[ $CHECK_ONLY != --check ]]; then
        sudo dnf config-manager addrepo --from-repofile=https://pkgs.tailscale.com/stable/fedora/tailscale.repo || \
            sudo dnf config-manager --add-repo https://pkgs.tailscale.com/stable/fedora/tailscale.repo
        sudo dnf install -y tailscale
        sudo systemctl enable --now tailscaled
        echo "  → next: sudo tailscale up --ssh   (join as node 'earth'; 'earth-ai' retires per #78)"
    fi
fi

# ── 7. Day-1 acceptance tests ────────────────────────────────────────────────
step "acceptance: rootless GPU via CDI"
if [[ -s /etc/cdi/nvidia.yaml ]] && command -v podman &>/dev/null && [[ $CHECK_ONLY != --check ]]; then
    if podman run --rm --device nvidia.com/gpu=all \
         docker.io/nvidia/cuda:12.8.0-base-ubi9 nvidia-smi --query-gpu=name --format=csv,noheader; then
        pass "rootless container sees the GPU"
    else
        echo "  ✖ rootless GPU test failed — escape hatch: run GPU units rootful (/etc/containers/systemd)"
        echo "    (no M0 container needs the GPU; this de-risks M1+)"
    fi
else
    todo "skipped (CDI spec or podman missing, or --check)"
fi

step "acceptance: SELinux :Z relabeled bind mount"
if [[ $CHECK_ONLY != --check ]]; then
    tmpd="$(mktemp -d)"; echo ok > "$tmpd/probe"
    if podman run --rm -v "$tmpd:/probe:ro,Z" registry.fedoraproject.org/fedora-minimal:44 cat /probe/probe >/dev/null; then
        pass ":Z bind mount works under enforcing SELinux"
    else
        echo "  ✖ :Z bind-mount test failed — check 'getenforce' and container_file_t labeling"
    fi
    rm -rf "$tmpd"
fi

echo
echo "Bootstrap complete. Re-run with --check for detect-only output."
