#!/usr/bin/env bash
# terrella — firewalld zones: loopback + tailnet exposure only (#10, ADR-0002).
#
# Fedora Workstation's default zone opens 1025-65535/tcp+udp to the LAN — that
# would expose host ollama (0.0.0.0:11434) and any accidental wide bind. This
# script creates a `terrella-lan` zone (same services, NO open port range),
# binds the LAN interface(s) to it, and puts tailscale0 in `trusted`.
#
# Idempotent; run with sudo available. `--check` prints without changing.

set -euo pipefail

CHECK_ONLY="${1:-}"
run() { if [[ $CHECK_ONLY == --check ]]; then echo "  would: $*"; else "$@"; fi; }

echo "▶ terrella-lan zone (FedoraWorkstation minus the 1025-65535 open range)"
if [[ $CHECK_ONLY != --check ]] && sudo firewall-cmd --permanent --get-zones | tr ' ' '\n' | grep -qx terrella-lan; then
    echo "  ✔ zone exists"
else
    run sudo firewall-cmd --permanent --new-zone=terrella-lan
    # Same service set as FedoraWorkstation on this host; ssh stays reachable
    # from the LAN (Tailscale SSH is the preferred path, but don't lock the door
    # while standing outside).
    for svc in dhcpv6-client ssh samba-client; do
        run sudo firewall-cmd --permanent --zone=terrella-lan --add-service="$svc"
    done
fi

# --new-zone only touches permanent config; the interface activation and
# --set-default-zone below operate on runtime, which doesn't know the zone
# until a reload (otherwise: "Error: INVALID_ZONE: terrella-lan").
run sudo firewall-cmd --reload

echo "▶ bind LAN interfaces to terrella-lan + make it the default zone"
DEFAULT_IFACE="$(ip -o -4 route show to default | awk '{print $5}' | head -1)"
if [[ -n $DEFAULT_IFACE && $DEFAULT_IFACE != tailscale0 ]]; then
    run sudo firewall-cmd --permanent --zone=terrella-lan --change-interface="$DEFAULT_IFACE"
    echo "  → $DEFAULT_IFACE"
fi
run sudo firewall-cmd --set-default-zone=terrella-lan

echo "▶ tailscale0 → trusted (tailnet is the remote access path)"
if ip link show tailscale0 &>/dev/null; then
    run sudo firewall-cmd --permanent --zone=trusted --change-interface=tailscale0
else
    echo "  ⚠ tailscale0 not present yet — re-run after 'tailscale up'"
fi

run sudo firewall-cmd --reload

echo
echo "▶ verify"
echo "  sudo firewall-cmd --get-active-zones"
echo "  From another LAN device: nmap -p 22,3000,4000,8080,9090,11434 <earth-lan-ip>"
echo "    → only 22 (ssh) may be open; 11434 must be closed"
echo "  From a container:        curl http://host.containers.internal:11434/api/version"
echo "    → must still work (pasta traffic is not LAN traffic)"
echo "  From a tailnet device:   curl http://earth:4000/health/liveness (after tailscale serve)"
