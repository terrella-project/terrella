#!/usr/bin/env bash
# Validate the quadlet stack the way systemd will load it.
#
#   scripts/ci/verify-quadlets.sh [DIR]    verify DIR (default: stack/quadlet)
#   scripts/ci/verify-quadlets.sh --self-test
#
# Two passes: podman's quadlet generator converts every .container/.volume/
# .network into a service unit (it rejects unknown keys), then
# `systemd-analyze --user verify` loads those plus DIR's plain .service and
# .target units. Needs podman and systemd (CI runs it in a Fedora container).
#
# Failure modes this guards, because each one passes silently otherwise:
# - systemd-analyze verify exits 0 on an unknown key or an unparsable value;
#   it only prints a warning. ANY output from it fails the check.
# - A generator that skips files (a relative dir, which it ignores; a renamed
#   binary) leaves nothing to verify, and verifying nothing passes. DIR is
#   made absolute, and every source must produce its unit.
# - Plain units that start a binary under %h (ollama.service) fail verify
#   when it is missing; a throwaway HOME gets an executable stub there.
# - `--user` verify needs a runtime dir; a CI container has none, and every
#   unit then "fails" for that reason alone. A private XDG_RUNTIME_DIR is set.
# --self-test feeds known-bad units through the same checks and fails unless
# each is rejected FOR ITS OWN REASON (the expected message must appear), and
# a good set is accepted.

set -euo pipefail

QUADLET_BIN=${QUADLET_BIN:-/usr/libexec/podman/quadlet}
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

die() { echo "verify-quadlets: $*" >&2; exit 1; }

# The unit a quadlet source file becomes.
generated_name() {
    local base=${1##*/}
    case $base in
        *.container) echo "${base%.container}.service" ;;
        *.volume) echo "${base%.volume}-volume.service" ;;
        *.network) echo "${base%.network}-network.service" ;;
        *) return 1 ;;
    esac
}

# verify DIR: 0 when every unit in DIR is valid, 1 (with the reasons) when not.
verify() {
    local src work out home run sources=() plain=() units=() f unit log
    [[ -d $1 ]] || die "no such directory: $1"
    # Absolute: the generator ignores a relative QUADLET_UNIT_DIRS and still
    # exits 0, having generated nothing.
    src=$(cd "$1" && pwd)
    work=$(mktemp -d)
    # shellcheck disable=SC2064  # expand now: $work is local
    trap "rm -rf '$work'" RETURN
    out=$work/units home=$work/home run=$work/run
    mkdir -p "$out" "$home" "$run"
    chmod 700 "$run"

    shopt -s nullglob
    sources=("$src"/*.container "$src"/*.volume "$src"/*.network)
    plain=("$src"/*.service "$src"/*.target)
    shopt -u nullglob
    (( ${#sources[@]} + ${#plain[@]} > 0 )) || die "no units in $src"

    if (( ${#sources[@]} > 0 )); then
        [[ -x $QUADLET_BIN ]] || die "quadlet generator not found at $QUADLET_BIN (install podman)"
        log=$work/quadlet.log
        if ! QUADLET_UNIT_DIRS=$src HOME=$home XDG_RUNTIME_DIR=$run "$QUADLET_BIN" -user "$out" >"$log" 2>&1; then
            cat "$log" >&2
            echo "verify-quadlets: the quadlet generator rejected $src" >&2
            return 1
        fi
        for f in "${sources[@]}"; do
            unit=$(generated_name "$f")
            [[ -f $out/$unit ]] || { echo "verify-quadlets: $f produced no $unit" >&2; return 1; }
        done
    fi

    for f in "${plain[@]}"; do
        cp "$f" "$out/"
        # ExecStart=%h/path: give the throwaway HOME an executable stub.
        sed -n 's|^ExecStart=[-@:+!]*%h/\([^ ]*\).*|\1|p' "$f" | while read -r rel; do
            mkdir -p "$home/$(dirname "$rel")"
            printf '#!/bin/sh\n' > "$home/$rel"
            chmod +x "$home/$rel"
        done
    done

    shopt -s nullglob
    units=("$out"/*.service "$out"/*.target)
    shopt -u nullglob
    log=$work/verify.log
    local rc=0
    HOME=$home XDG_RUNTIME_DIR=$run SYSTEMD_UNIT_PATH="$out:" systemd-analyze --user verify "${units[@]}" >"$log" 2>&1 || rc=$?
    if (( rc != 0 )) || [[ -s $log ]]; then
        cat "$log" >&2
        echo "verify-quadlets: systemd-analyze verify reported problems in $src (exit $rc)" >&2
        return 1
    fi
    echo "verify-quadlets: ${#sources[@]} quadlet + ${#plain[@]} plain units in $src: OK (${#units[@]} units verified)"
}

# Each case is a directory of units that must be rejected, with the message
# that says why; a rejection for any other reason is a self-test failure.
self_test() {
    local root failed=0 name expect
    root=$(mktemp -d)
    # shellcheck disable=SC2064
    trap "rm -rf '$root'" RETURN
    mkdir -p "$root"/{quadlet-key,systemd-key,systemd-value,missing-dep,good}

    printf '[Container]\nImage=docker.io/library/alpine\nNotAKey=1\n' \
        > "$root/quadlet-key/x.container"
    printf '[Unit]\nDescription=x\n[Container]\nImage=docker.io/library/alpine\n[Service]\nRestartt=always\n' \
        > "$root/systemd-key/x.container"
    printf '[Unit]\nDescription=x\n[Service]\nType=bogus\nExecStart=/bin/true\n' \
        > "$root/systemd-value/x.service"
    printf '[Unit]\nDescription=x\nRequires=not-there.service\n[Service]\nExecStart=/bin/true\n' \
        > "$root/missing-dep/x.service"
    printf '[Unit]\nDescription=x\n[Container]\nImage=docker.io/library/alpine\n' \
        > "$root/good/x.container"
    printf '[Unit]\nDescription=x\n[Service]\nExecStart=%%h/.local/bin/stub serve\n' \
        > "$root/good/y.service"

    local -A expected=(
        [quadlet-key]="unsupported key 'NotAKey'"
        [systemd-key]="Unknown key 'Restartt'"
        [systemd-value]="Failed to parse Type=bogus"
        [missing-dep]="not-there.service not found"
    )
    for name in quadlet-key systemd-key systemd-value missing-dep; do
        expect=${expected[$name]}
        if verify "$root/$name" >"$root/$name.log" 2>&1; then
            echo "verify-quadlets: self-test: '$name' was NOT rejected" >&2
            failed=1
        elif grep -qF -- "$expect" "$root/$name.log"; then
            echo "verify-quadlets: self-test: '$name' rejected: $expect"
        else
            cat "$root/$name.log" >&2
            echo "verify-quadlets: self-test: '$name' rejected, but not for \"$expect\"" >&2
            failed=1
        fi
    done
    # Given as a relative path, the way CI passes stack/quadlet.
    if (cd "$root" && verify good) >"$root/good.log" 2>&1 \
        && grep -q '1 quadlet + 1 plain units' "$root/good.log"; then
        echo "verify-quadlets: self-test: 'good' accepted (relative path)"
    else
        cat "$root/good.log" >&2
        echo "verify-quadlets: self-test: 'good' was rejected" >&2
        failed=1
    fi
    return "$failed"
}

case ${1:-} in
    --self-test) self_test ;;
    -h|--help) sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//' ;;
    *) verify "${1:-$REPO_ROOT/stack/quadlet}" ;;
esac
