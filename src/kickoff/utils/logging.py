"""Console output helpers."""

from rich.console import Console

console = Console()


def info(message: str) -> None:
    console.print(f"[cyan]ℹ[/cyan] {message}")


def success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def warning(message: str) -> None:
    console.print(f"[yellow]⚠[/yellow] {message}")


def error(message: str) -> None:
    console.print(f"[red]✗[/red] {message}")


def step(message: str) -> None:
    console.print(f"\n[bold blue]→[/bold blue] [bold]{message}[/bold]")
