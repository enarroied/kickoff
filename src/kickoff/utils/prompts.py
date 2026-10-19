"""Interactive prompts."""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Confirm

console = Console()


def confirm(message: str, default: bool = True) -> bool:
    return Confirm.ask(message, default=default, console=console)
