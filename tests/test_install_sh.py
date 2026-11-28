"""install.sh, run against stand-ins for uv, curl and wget.

Each test builds a PATH holding only the system tools the script needs plus
the stand-ins it chooses, so the real uv on the machine is never seen and
nothing touches the network.
"""

import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

INSTALL_SH = Path(__file__).resolve().parent.parent / "install.sh"
SYSTEM_TOOLS = ("sh", "cat", "chmod", "mkdir", "id", "grep")
UV_INSTALLER_URL = "https://astral.sh/uv/install.sh"

# A stand-in uv: answers --version and `tool dir --bin`, and on
# `tool install` logs its arguments and drops a terrella command in the tool
# bin dir. FAKE_UV_FAIL_INSTALL / FAKE_UV_NO_COMMAND make the install fail or
# leave no command behind.
FAKE_UV = """#!/bin/sh
case "$1 $2" in
  "--version ") echo "uv 0.0.0-test" ;;
  "tool dir") echo "$FAKE_TOOL_BIN" ;;
  "tool install")
    echo "$*" >> "$FAKE_LOG"
    [ -z "${FAKE_UV_FAIL_INSTALL:-}" ] || exit 3
    [ -n "${FAKE_UV_NO_COMMAND:-}" ] && exit 0
    mkdir -p "$FAKE_TOOL_BIN"
    printf '#!/bin/sh\\necho "terrella 9.9.9-test"\\n' > "$FAKE_TOOL_BIN/terrella"
    chmod +x "$FAKE_TOOL_BIN/terrella"
    ;;
  *) echo "fake uv: unexpected: $*" >&2; exit 64 ;;
esac
"""

# What the stand-in downloaders serve as uv's installer: it puts the fake uv
# where uv's real installer would, ~/.local/bin.
FAKE_UV_INSTALLER = (
    'mkdir -p "$HOME/.local/bin"\n'
    "cat > \"$HOME/.local/bin/uv\" <<'UV'\n" + FAKE_UV + "UV\n"
    'chmod +x "$HOME/.local/bin/uv"\n'
)


def _write_exe(path: Path, body: str) -> None:
    # Replace, never write through: the path may be a symlink to a real
    # system tool (see the env fixture).
    path.unlink(missing_ok=True)
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _downloader(name: str, log: Path, served: Path, fail: bool, help_text: str) -> str:
    # Answers --help with help_text; otherwise logs "<name> <args>" and prints
    # the served file, or fails like curl -f.
    action = "exit 22" if fail else f'cat "{served}"'
    return (
        "#!/bin/sh\n"
        f'if [ "$1" = --help ]; then echo "{help_text}"; exit 0; fi\n'
        f'echo "{name} $*" >> "{log}"\n'
        f"{action}\n"
    )


@dataclass
class Env:
    tmp: Path
    tools: Path
    home: Path
    tool_bin: Path
    log: Path
    served: Path

    def add_uv(self) -> None:
        _write_exe(self.tools / "uv", FAKE_UV)

    def add_downloader(self, name: str, *, fail: bool = False, help_text: str = "") -> None:
        _write_exe(self.tools / name, _downloader(name, self.log, self.served, fail, help_text))

    def add_fake_root(self) -> None:
        _write_exe(self.tools / "id", "#!/bin/sh\necho 0\n")

    def run(
        self,
        script: Path = INSTALL_SH,
        *,
        extra_path: tuple[Path, ...] = (),
        **env: str,
    ) -> subprocess.CompletedProcess[str]:
        path = os.pathsep.join(str(p) for p in (*extra_path, self.tools))
        full_env = {
            "PATH": path,
            "HOME": str(self.home),
            "FAKE_TOOL_BIN": str(self.tool_bin),
            "FAKE_LOG": str(self.log),
            **env,
        }
        return subprocess.run(
            [str(self.tools / "sh"), str(script)],
            env=full_env,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def env(tmp_path: Path) -> Env:
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in SYSTEM_TOOLS:
        found = shutil.which(name)
        assert found, f"{name} is needed to run these tests"
        (tools / name).symlink_to(found)
    home = tmp_path / "home"
    home.mkdir()
    served = tmp_path / "uv-installer.sh"
    served.write_text(FAKE_UV_INSTALLER)
    return Env(
        tmp=tmp_path,
        tools=tools,
        home=home,
        tool_bin=tmp_path / "tool-bin",
        log=tmp_path / "calls.log",
        served=served,
    )


def test_with_uv_present_it_installs_terrella_from_pypi(env: Env) -> None:
    env.add_uv()
    proc = env.run()
    assert proc.returncode == 0, proc.stderr
    assert env.calls() == ["tool install --upgrade terrella"]
    assert "using uv 0.0.0-test" in proc.stdout
    assert "installed terrella 9.9.9-test" in proc.stdout


def test_terrella_spec_is_passed_to_uv_unchanged(env: Env) -> None:
    env.add_uv()
    spec = "git+https://github.com/terrella-project/terrella"
    proc = env.run(TERRELLA_SPEC=spec)
    assert proc.returncode == 0, proc.stderr
    assert env.calls() == [f"tool install --upgrade {spec}"]


def test_an_empty_terrella_spec_means_the_default(env: Env) -> None:
    env.add_uv()
    proc = env.run(TERRELLA_SPEC="")
    assert proc.returncode == 0, proc.stderr
    assert env.calls() == ["tool install --upgrade terrella"]


def test_it_says_how_to_fix_path_when_the_tool_bin_dir_is_missing(env: Env) -> None:
    env.add_uv()
    proc = env.run()
    assert proc.returncode == 0, proc.stderr
    assert "uv tool update-shell" in proc.stdout


def test_no_path_advice_when_the_tool_bin_dir_is_on_path(env: Env) -> None:
    env.add_uv()
    proc = env.run(extra_path=(env.tool_bin,))
    assert proc.returncode == 0, proc.stderr
    assert "update-shell" not in proc.stdout


@pytest.mark.parametrize("downloader", ["curl", "wget"])
def test_without_uv_it_installs_uv_first(env: Env, downloader: str) -> None:
    env.add_downloader(downloader)
    proc = env.run()
    assert proc.returncode == 0, proc.stderr
    calls = env.calls()
    assert calls[0].startswith(f"{downloader} ")
    assert calls[0].endswith(UV_INSTALLER_URL)
    assert calls[1:] == ["tool install --upgrade terrella"]
    assert (env.home / ".local/bin/uv").exists()
    assert "installed uv 0.0.0-test" in proc.stdout


def test_a_uv_from_an_earlier_run_off_path_is_reused(env: Env) -> None:
    # The first run put uv in ~/.local/bin, which a fresh login may not have
    # on PATH yet; a second run must use it, not download uv again.
    local_bin = env.home / ".local/bin"
    local_bin.mkdir(parents=True)
    _write_exe(local_bin / "uv", FAKE_UV)
    env.add_downloader("curl")
    proc = env.run()
    assert proc.returncode == 0, proc.stderr
    assert env.calls() == ["tool install --upgrade terrella"]
    assert f"from {local_bin}/uv" in proc.stdout


def test_path_advice_judges_the_users_path_not_the_scripts(env: Env) -> None:
    # The script adds ~/.local/bin to its own PATH to find a fresh uv. When
    # uv's tool bin dir is that same ~/.local/bin, the user still needs the
    # advice: their shell's PATH does not have it.
    env.add_downloader("curl")
    proc = env.run(FAKE_TOOL_BIN=str(env.home / ".local/bin"))
    assert proc.returncode == 0, proc.stderr
    assert "uv tool update-shell" in proc.stdout


def test_curl_is_preferred_over_wget(env: Env) -> None:
    env.add_downloader("curl")
    env.add_downloader("wget")
    proc = env.run()
    assert proc.returncode == 0, proc.stderr
    assert env.calls()[0].startswith("curl ")


def test_downloads_are_https_only(env: Env) -> None:
    env.add_downloader("curl")
    env.run()
    assert "--proto =https" in env.calls()[0]


def test_gnu_wget_refuses_redirects_off_https(env: Env) -> None:
    env.add_downloader("wget", help_text="  --https-only   only follow secure HTTPS links")
    proc = env.run()
    assert proc.returncode == 0, proc.stderr
    assert env.calls()[0] == f"wget --https-only -qO- {UV_INSTALLER_URL}"


def test_busybox_wget_without_https_only_still_works(env: Env) -> None:
    # Alpine's busybox wget has no --https-only and fails on the flag.
    env.add_downloader("wget", help_text="BusyBox wget: -q -O FILE")
    proc = env.run()
    assert proc.returncode == 0, proc.stderr
    assert env.calls()[0] == f"wget -qO- {UV_INSTALLER_URL}"


def test_uv_install_dir_is_searched_for_the_new_uv(env: Env) -> None:
    # A uv installer honouring UV_INSTALL_DIR puts uv there, not ~/.local/bin.
    custom = env.tmp / "custom-bin"
    env.served.write_text(FAKE_UV_INSTALLER.replace("$HOME/.local/bin", str(custom)))
    env.add_downloader("curl")
    proc = env.run(UV_INSTALL_DIR=str(custom))
    assert proc.returncode == 0, proc.stderr
    assert (custom / "uv").exists()


def test_without_uv_curl_or_wget_it_stops_with_advice(env: Env) -> None:
    proc = env.run()
    assert proc.returncode == 1
    assert "neither curl nor wget" in proc.stderr
    assert env.calls() == []


def test_a_failed_uv_download_runs_nothing(env: Env) -> None:
    env.add_downloader("curl", fail=True)
    proc = env.run()
    assert proc.returncode == 1
    assert "could not download the uv installer" in proc.stderr
    assert not (env.home / ".local/bin/uv").exists()
    assert not any(c.startswith("tool install") for c in env.calls())


def test_a_uv_installer_that_leaves_no_uv_is_reported(env: Env) -> None:
    env.served.write_text("true\n")
    env.add_downloader("curl")
    proc = env.run()
    assert proc.returncode == 1
    assert "not on PATH" in proc.stderr


def test_a_failed_tool_install_is_reported(env: Env) -> None:
    env.add_uv()
    proc = env.run(FAKE_UV_FAIL_INSTALL="1")
    assert proc.returncode == 1
    assert "uv tool install terrella failed" in proc.stderr


def test_an_install_without_a_terrella_command_is_reported(env: Env) -> None:
    # e.g. TERRELLA_SPEC names a version older than the CLI, such as the
    # 0.0.1 name-reservation stub on PyPI.
    env.add_uv()
    proc = env.run(FAKE_UV_NO_COMMAND="1")
    assert proc.returncode == 1
    assert "terrella is not in" in proc.stderr


def test_it_refuses_to_run_as_root(env: Env) -> None:
    env.add_uv()
    env.add_fake_root()
    proc = env.run()
    assert proc.returncode == 1
    assert "not root" in proc.stderr
    assert env.calls() == []


def test_a_download_cut_off_before_the_last_line_runs_nothing(env: Env) -> None:
    # `curl ... | sh` runs whatever arrived. Everything happens in main(),
    # called on the last line, so any cut before it defines functions and
    # does nothing else.
    env.add_uv()
    text = INSTALL_SH.read_text()
    last_line = 'main "$@"\n'
    assert text.endswith(last_line)
    cut = env.tmp / "cut.sh"
    cut.write_text(text[: -len(last_line)])
    proc = env.run(cut)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert env.calls() == []
