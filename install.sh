#!/bin/sh
# Bootstrap the terrella CLI: install uv if it is missing, then install
# terrella as a uv tool (ADR-0001).
#
#   curl -LsSf https://raw.githubusercontent.com/terrella-project/terrella/main/install.sh | sh
#
# Environment:
#   TERRELLA_SPEC   what `uv tool install` installs (default: terrella, from PyPI).
#                   Any uv requirement works, e.g. a version (terrella==0.1.0) or
#                   the main branch (git+https://github.com/terrella-project/terrella).
#   UV_INSTALL_DIR  where a fresh uv goes (default: uv's own, ~/.local/bin).
#
# Run it again to upgrade: it reinstalls the newest version that TERRELLA_SPEC
# allows. Installs nothing as root and changes no system files; uv's installer
# may add ~/.local/bin to your shell's PATH.
#
# POSIX sh, because `| sh` is often dash. Everything runs from main() at the
# very end, so a download cut off half-way runs nothing.

set -eu

UV_INSTALLER_URL="https://astral.sh/uv/install.sh"

say() {
    printf 'terrella-install: %s\n' "$*"
}

die() {
    printf 'terrella-install: error: %s\n' "$*" >&2
    exit 1
}

# Print the URL's body on stdout, with whichever downloader exists.
fetch() {
    if command -v curl >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 -LsSf "$1"
    elif command -v wget >/dev/null 2>&1; then
        # GNU wget can refuse a redirect off https; busybox wget has no
        # such flag, and the URL itself is https either way.
        if wget --help 2>&1 | grep -q -- '--https-only'; then
            wget --https-only -qO- "$1"
        else
            wget -qO- "$1"
        fi
    else
        die "neither curl nor wget is installed; install one and run this again"
    fi
}

# uv's installer puts uv in one of these, and a fresh shell may not have them
# on PATH yet.
add_uv_dirs_to_path() {
    for dir in ${UV_INSTALL_DIR:+"$UV_INSTALL_DIR"} "${XDG_BIN_HOME:-}" "$HOME/.local/bin" "$HOME/.cargo/bin"; do
        [ -n "$dir" ] && [ -d "$dir" ] && PATH="$dir:$PATH"
    done
    export PATH
}

ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        say "using $(uv --version)"
        return
    fi
    # A uv from an earlier run may sit in its install dir, off this PATH.
    add_uv_dirs_to_path
    if command -v uv >/dev/null 2>&1; then
        say "using $(uv --version) from $(command -v uv)"
        return
    fi
    say "uv not found; installing it from $UV_INSTALLER_URL"
    # Download first, run second: a failed download must not reach sh.
    installer=$(fetch "$UV_INSTALLER_URL") || die "could not download the uv installer"
    printf '%s\n' "$installer" | sh || die "the uv installer failed"
    add_uv_dirs_to_path
    command -v uv >/dev/null 2>&1 || die "uv was installed but is not on PATH; open a new shell and run this again"
    say "installed $(uv --version)"
}

main() {
    [ "$(id -u)" -ne 0 ] || die "run this as your own user, not root: terrella installs per user"

    spec=${TERRELLA_SPEC:-terrella}
    # The PATH the user's shell has; ensure_uv may add uv's dirs to ours.
    user_path=$PATH
    ensure_uv

    say "installing $spec"
    uv tool install --upgrade "$spec" || die "uv tool install $spec failed"

    # uv puts tool commands in its tool bin dir; find the new command there
    # even when that dir is not on PATH yet.
    bin_dir=$(uv tool dir --bin) || die "uv could not report its tool bin dir"
    [ -x "$bin_dir/terrella" ] || die "terrella is not in $bin_dir after the install"
    say "installed $("$bin_dir/terrella" --version)"

    case ":$user_path:" in
        *":$bin_dir:"*) ;;
        *) say "$bin_dir is not on your PATH; run 'uv tool update-shell', then open a new shell" ;;
    esac
}

main "$@"
