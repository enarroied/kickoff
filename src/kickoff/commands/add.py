"""The `kickoff add` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from kickoff.adding import FEATURE_CHOICES, SUFFIX, AddPlan, build_plan, write_manifest, write_plan
from kickoff.config import load_config
from kickoff.exceptions import KickoffError, ValidationError
from kickoff.utils import logging
from kickoff.utils.prompts import confirm
from kickoff.utils.shell import command_exists, run


def add_command(
    feature: Annotated[str, typer.Argument(help=f"One of: {', '.join(FEATURE_CHOICES)}")],
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project directory (default: current directory)"),
    ] = None,
    dbt_adapter: Annotated[
        str | None, typer.Option("--dbt-adapter", help="postgres, duckdb or sqlite (dbt only)")
    ] = None,
    traefik_domain: Annotated[
        str | None, typer.Option("--traefik-domain", help="Base domain (traefik only)")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show the plan, change nothing")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation")] = False,
) -> None:
    """Add a feature to a project that was created with kickoff."""
    project_dir = (path or Path.cwd()).resolve()
    config = load_config()
    try:
        if dbt_adapter is None and feature == "dbt":
            dbt_adapter = config["defaults"]["dbt_adapter"]
        plan = build_plan(
            project_dir, feature, dbt_adapter=dbt_adapter, traefik_domain=traefik_domain
        )
        _print_plan(plan)
        if dry_run:
            logging.info("Dry run — no changes made")
            return
        if not yes and not confirm("Apply these changes?", default=True):
            logging.warning("Aborted by user")
            raise typer.Exit(code=1)
        _apply(project_dir, plan)
        _print_followups(plan)
    except KickoffError as exc:
        logging.error(str(exc))
        raise typer.Exit(code=1) from exc


def _print_plan(plan: AddPlan) -> None:
    logging.info(f"Adding [bold]{plan.feature}[/bold] to {plan.new_spec.name}")
    for label, items in (
        ("create", plan.create),
        ("replace (unmodified generated file)", plan.overwrite),
        (f"write next to the existing file as *{SUFFIX} (you changed it)", plan.conflicts),
    ):
        for relative in items:
            logging.info(f"  {label}: {relative}")
    for directory in plan.directories:
        logging.info(f"  create folder: {directory}")
    if plan.dependencies or plan.dev_dependencies:
        logging.info(f"  uv add {' '.join(plan.dependencies)}".rstrip())
        if plan.dev_dependencies:
            logging.info(f"  uv add --dev {' '.join(plan.dev_dependencies)}")
    if plan.env_added:
        logging.info(f"  .env: add {', '.join(plan.env_added)}")
    if plan.gitignore_lines:
        logging.info(f"  .gitignore: add {len(plan.gitignore_lines)} line(s)")
    for notice in plan.notices:
        logging.warning(notice)


def _apply(project_dir: Path, plan: AddPlan) -> None:
    if (plan.dependencies or plan.dev_dependencies) and not command_exists("uv"):
        raise ValidationError("`uv` is required but not found on PATH.")
    write_plan(project_dir, plan)
    if plan.dependencies:
        run(["uv", "add", *plan.dependencies], cwd=project_dir)
    if plan.dev_dependencies:
        run(["uv", "add", "--dev", *plan.dev_dependencies], cwd=project_dir)
    write_manifest(project_dir, plan)
    logging.success(f"Added {plan.feature}")


def _print_followups(plan: AddPlan) -> None:
    if plan.conflicts:
        logging.warning(
            f"Merge the *{SUFFIX} files into your versions, then delete them: "
            + ", ".join(plan.conflicts)
        )
    for name, value in plan.env_changed.items():
        logging.warning(f"Update {name} in .env yourself, a new value is expected: {value}")
    logging.info("README.md and AGENTS.md were not changed. You may want to add:")
    for label, command in plan.commands.items():
        logging.info(f"  {label}: {command}")
    for badge in plan.badges:
        logging.info(f"  badge: {badge}")
    logging.info("Review with `git status` and `git diff`; nothing was committed.")
