"""The `kickoff config` command group."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Annotated, Any

import tomlkit
import typer

from kickoff import config as cfg
from kickoff import defaults
from kickoff.features.dbt_adapters import ADAPTERS
from kickoff.registry import all_templates
from kickoff.utils import logging

app = typer.Typer(help="Manage kickoff global configuration", no_args_is_help=True)

MAX_PORT = 65535

# Keys whose value must be one of a fixed set.
CHOICES: dict[str, tuple[str, ...]] = {
    "defaults.python_version": defaults.SUPPORTED_PYTHON_VERSIONS,
    "defaults.license": defaults.SUPPORTED_LICENSES,
    "defaults.repo_visibility": ("public", "private"),
    "defaults.server": defaults.SUPPORTED_SERVERS,
    "defaults.dbt_adapter": tuple(ADAPTERS),
    "docker.default_db": defaults.SUPPORTED_DATABASES,
}
PORT_KEYS = ("docker.default_app_port", "docker.default_db_port")


def known_keys() -> list[str]:
    return [f"{section}.{key}" for section, values in cfg.DEFAULT_CONFIG.items() for key in values]


def coerce_and_validate(key: str, raw: str) -> Any:
    """Convert `raw` to the type of the key's default and check it. Raises typer.BadParameter."""
    if key not in known_keys():
        raise typer.BadParameter(f"Unknown key '{key}'. Known keys: {', '.join(known_keys())}")
    section, name = key.split(".", 1)
    default = cfg.DEFAULT_CONFIG[section][name]
    value: Any = raw
    if isinstance(default, bool):
        if raw.lower() not in ("true", "false"):
            raise typer.BadParameter(f"{key} must be true or false")
        value = raw.lower() == "true"
    elif isinstance(default, int):
        try:
            value = int(raw)
        except ValueError as exc:
            raise typer.BadParameter(f"{key} must be a number") from exc
        if key in PORT_KEYS and not 1 <= value <= MAX_PORT:
            raise typer.BadParameter(f"{key} must be between 1 and {MAX_PORT}")
    if key in CHOICES and value not in CHOICES[key]:
        raise typer.BadParameter(f"{key} must be one of: {', '.join(CHOICES[key])}")
    if key == "defaults.template":
        templates, _ = all_templates()
        if value not in templates:
            raise typer.BadParameter(f"{key} must be one of: {', '.join(sorted(templates))}")
    return value


def open_editor(path: Path) -> None:
    """Open `path` in $VISUAL / $EDITOR (nano or vi as a fallback) and wait for it to close."""
    command = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not command:
        command = next((name for name in ("nano", "vi") if shutil.which(name)), None)
    if not command:
        raise typer.BadParameter("No editor found. Set $EDITOR, e.g. export EDITOR=nano")
    subprocess.run([*shlex.split(command), str(path)], check=False)


def _ensure_file() -> None:
    path = cfg.config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# kickoff global configuration\n" + tomlkit.dumps(cfg.DEFAULT_CONFIG),
            encoding="utf-8",
        )


@app.command("path")
def path() -> None:
    """Print where the configuration file lives."""
    logging.console.print(str(cfg.config_path()))


@app.command("show")
def show() -> None:
    """Display the current configuration."""
    logging.console.print(json.dumps(cfg.load_config(), indent=2))


@app.command("init")
def init() -> None:
    """Create the config file (with the built-in defaults) if it doesn't exist."""
    target = cfg.config_path()
    if target.exists():
        logging.warning(f"Config already exists at {target}")
        return
    _ensure_file()
    logging.success(f"Created config at {target}")


@app.command("set")
def set_value(
    key: Annotated[str, typer.Argument(help="section.key, e.g. defaults.python_version")],
    value: Annotated[str, typer.Argument(help="New value")],
) -> None:
    """Change one value (comments and layout of the file are kept)."""
    typed = coerce_and_validate(key, value)
    _ensure_file()
    target = cfg.config_path()
    document = tomlkit.parse(target.read_text(encoding="utf-8"))
    section, name = key.split(".", 1)
    if section not in document:
        document[section] = tomlkit.table()
    document[section][name] = typed  # type: ignore[index]
    target.write_text(tomlkit.dumps(document), encoding="utf-8")
    logging.success(f"{key} = {typed!r}")


@app.command("edit")
def edit() -> None:
    """Open the config in $VISUAL / $EDITOR, then check it."""
    _ensure_file()
    target = cfg.config_path()
    open_editor(target)
    try:
        data = tomllib.loads(target.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        logging.error(f"{target} is not valid TOML: {exc}")
        raise typer.Exit(code=1) from exc
    problems = []
    for section, values in data.items():
        for name, raw in (values.items() if isinstance(values, dict) else []):
            key = f"{section}.{name}"
            try:
                coerce_and_validate(key, str(raw).lower() if isinstance(raw, bool) else str(raw))
            except typer.BadParameter as exc:
                problems.append(exc.message)
    for problem in problems:
        logging.warning(problem)
    if not problems:
        logging.success("Config saved and valid")
