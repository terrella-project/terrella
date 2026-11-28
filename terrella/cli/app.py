"""The root ``terrella`` command.

Subcommands register on ``app`` as they land: ``apply`` (#19), ``provision``
(#21), ``smoke``/``status``/``logs`` (#22).
"""

from typing import Annotated

import typer

from terrella import __version__

app = typer.Typer(
    name="terrella",
    help="Provision and manage a personal AI stack from one terrella.yaml.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"terrella {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_print_version,
            is_eager=True,
            help="Print the version and exit.",
        ),
    ] = False,
) -> None:
    """Provision and manage a personal AI stack from one terrella.yaml."""


def main() -> None:
    """Entry point for the ``terrella`` console script."""
    app(prog_name="terrella")
