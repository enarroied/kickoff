"""Typer entry point for kickoff."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kickoff import __version__
from kickoff.commands import config_cmd
from kickoff.commands.add import add_command
from kickoff.commands.new import new_command
from kickoff.registry import all_templates
from kickoff.utils.logging import console

app = typer.Typer(
    name="kickoff",
    help="Scaffold new development projects with one command.",
    no_args_is_help=True,
)

app.command("new")(new_command)
app.command("add")(add_command)
app.add_typer(config_cmd.app, name="config")


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"kickoff {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """Scaffold new development projects with one command."""
    del version  # handled by the eager callback


@app.command("templates")
def templates() -> None:
    """List available templates (built-in and custom)."""
    entries, errors = all_templates()
    table = Table(title="Available templates")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Source")
    for name, entry in entries.items():
        table.add_row(name, entry.template.description, entry.source)
    console.print(table)
    for file, message in errors.items():
        console.print(f"[yellow]⚠[/yellow] custom template {file} ignored: {message}")
