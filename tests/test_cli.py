"""The root ``terrella`` command: version, help, and how it is started."""

import subprocess
import sys
from importlib.metadata import version

import pytest
from typer.testing import CliRunner

import terrella
from terrella.cli import app

runner = CliRunner()


@pytest.mark.parametrize("flag", ["--version", "-V"])
def test_version_flag_prints_the_package_version(flag: str) -> None:
    result = runner.invoke(app, [flag])
    assert result.exit_code == 0
    assert result.output == f"terrella {terrella.__version__}\n"


def test_version_flag_wins_over_a_command_that_does_not_exist() -> None:
    # --version is eager: it answers before the command name is looked up.
    result = runner.invoke(app, ["--version", "no-such-command"])
    assert result.exit_code == 0
    assert result.output == f"terrella {terrella.__version__}\n"


def test_installed_metadata_matches_the_source_version() -> None:
    # pyproject.toml reads the version from terrella/__init__.py at build
    # time; the two must never drift.
    assert version("terrella") == terrella.__version__


def test_no_arguments_shows_the_help() -> None:
    result = runner.invoke(app, [])
    # Click 8.2+ exits 2 when no_args_is_help prints the help.
    assert result.exit_code == 2
    assert "Usage: terrella" in result.output
    assert "--version" in result.output


def test_help_names_the_program_and_its_purpose() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage: terrella" in result.output
    assert "terrella.yaml" in result.output


def test_an_unknown_command_is_a_usage_error() -> None:
    result = runner.invoke(app, ["no-such-command"])
    assert result.exit_code == 2
    assert "No such command" in result.output


def test_python_dash_m_runs_the_same_cli() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "terrella", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == f"terrella {terrella.__version__}\n"
