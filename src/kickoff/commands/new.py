"""The `kickoff new` command."""

from __future__ import annotations

import re
import secrets
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer

from kickoff.config import load_config
from kickoff.defaults import (
    PROJECT_NAME_PATTERN,
    SUPPORTED_DATABASES,
    SUPPORTED_LICENSES,
    SUPPORTED_PYTHON_VERSIONS,
    SUPPORTED_SERVERS,
)
from kickoff.dependencies import production_dependencies
from kickoff.exceptions import ExternalCommandError, KickoffError, ValidationError
from kickoff.features import apply_features
from kickoff.features.dbt_adapters import ADAPTERS
from kickoff.generators import ci, files, git, github, licenses, opencode, pyproject, structure
from kickoff.generators.commands import project_commands
from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.registry import get_template
from kickoff.utils import logging
from kickoff.utils.prompts import confirm
from kickoff.utils.shell import command_exists, run


@dataclass
class _Outcome:
    hooks_installed: bool = False
    github_created: bool = False


def new_command(
    name: Annotated[str, typer.Argument(help="Project name")],
    template: Annotated[
        str | None,
        typer.Option("--template", "-t", help="default, django or jupyter (default: config)"),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Parent directory (default: current directory)"),
    ] = None,
    python_version: Annotated[
        str | None, typer.Option("--python", help="Python version (default: from config)")
    ] = None,
    license_name: Annotated[
        str | None,
        typer.Option("--license", help="MIT, Apache-2.0, GPL-3.0 or none (default: from config)"),
    ] = None,
    private: Annotated[
        bool | None,
        typer.Option("--private/--public", help="Repo visibility (default: from config)"),
    ] = None,
    no_github: Annotated[
        bool, typer.Option("--no-github", help="Skip GitHub repo creation")
    ] = False,
    no_git: Annotated[bool, typer.Option("--no-git", help="Skip git init")] = False,
    no_push: Annotated[bool, typer.Option("--no-push", help="Create repo but do not push")] = False,
    no_ci: Annotated[bool, typer.Option("--no-ci", help="Skip GitHub Actions")] = False,
    no_opencode: Annotated[
        bool, typer.Option("--no-opencode", help="Skip OpenCode files")
    ] = False,
    server: Annotated[
        str | None,
        typer.Option("--server", help="uvicorn or gunicorn, Django only (default: from config)"),
    ] = None,
    with_prefect: Annotated[
        bool, typer.Option("--with-prefect", help="Add Prefect (example flow, prefect.yaml)")
    ] = False,
    with_dbt: Annotated[
        bool, typer.Option("--with-dbt", help="Add a dbt project in dbt/")
    ] = False,
    dbt_adapter: Annotated[
        str | None,
        typer.Option("--dbt-adapter", help="postgres, duckdb or sqlite; needs --with-dbt"),
    ] = None,
    docker: Annotated[bool, typer.Option("--docker", help="Enable Docker artifacts")] = False,
    db: Annotated[
        str | None,
        typer.Option("--db", help="none, postgres or postgis; implies --docker"),
    ] = None,
    db_password: Annotated[
        str | None,
        typer.Option("--db-password", help="Database password (default: generated)"),
    ] = None,
    expose_db: Annotated[
        bool, typer.Option("--expose-db", help="Publish the database port on 127.0.0.1")
    ] = False,
    db_port: Annotated[
        int | None,
        typer.Option("--db-port", help="Host port of the database; needs --expose-db"),
    ] = None,
    app_port: Annotated[
        int | None,
        typer.Option("--app-port", help="Host port of the app (default: from config, 8000)"),
    ] = None,
    with_pgadmin: Annotated[
        bool, typer.Option("--with-pgadmin", help="Add a pgAdmin service; needs --db")
    ] = False,
    with_redis: Annotated[
        bool, typer.Option("--with-redis", help="Add a Redis service (implies --docker)")
    ] = False,
    with_minio: Annotated[
        bool, typer.Option("--with-minio", help="Add an S3 store, MinIO API (implies --docker)")
    ] = False,
    with_mail: Annotated[
        bool, typer.Option("--with-mail", help="Add Mailpit, a mail catcher (implies --docker)")
    ] = False,
    traefik: Annotated[
        bool, typer.Option("--traefik", help="Route through an existing Traefik (implies --docker)")
    ] = False,
    traefik_domain: Annotated[
        str | None,
        typer.Option("--traefik-domain", help="Base domain for Traefik hosts; needs --traefik"),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Allow an existing target directory")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show plan without executing")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Non-interactive")] = False,
) -> None:
    """Create a new project."""
    config = load_config()
    defaults = config["defaults"]
    author_name, author_email = _resolve_author(config)
    database = db or config["docker"]["default_db"]
    # A database, a service or Traefik always come with Docker.
    needs_docker = (
        database != "none" or with_redis or with_minio or with_mail or traefik or with_pgadmin
    )
    use_docker = docker or needs_docker

    spec = ProjectSpec(
        name=name,
        path=(path or Path.cwd()).resolve(),
        template=template or defaults["template"],
        python_version=python_version or defaults["python_version"],
        license=license_name or defaults["license"],
        branch=defaults["branch"],
        server=server or defaults["server"],
        features=[
            feature
            for feature, enabled in (
                ("prefect", with_prefect),
                ("dbt", with_dbt),
                ("docker", use_docker),
            )
            if enabled
        ],
        dbt_adapter=dbt_adapter or defaults["dbt_adapter"],
        author_name=author_name,
        author_email=author_email,
        github_owner=config["user"]["github_username"] or None,
        private=private if private is not None else defaults["repo_visibility"] == "private",
        create_git=not no_git,
        # A GitHub repository needs a local git repository.
        create_github=config["github"]["create_repo"] and not no_github and not no_git,
        push_initial=config["github"]["push_initial"] and not no_push,
        enable_ci=not no_ci,
        enable_opencode=not no_opencode,
        docker=use_docker,
        db=database,
        db_password=db_password,
        expose_db=expose_db,
        with_pgadmin=with_pgadmin,
        with_redis=with_redis,
        with_minio=with_minio,
        with_mail=with_mail,
        minio_image=config["docker"]["minio_image"],
        traefik=traefik,
        traefik_domain=traefik_domain or config["docker"]["traefik_domain"],
        traefik_network=config["docker"]["traefik_network"],
        traefik_entrypoint=config["docker"]["traefik_entrypoint"],
        traefik_cert_resolver=config["docker"]["traefik_cert_resolver"],
        db_port=db_port or config["docker"]["default_db_port"],
        app_port=app_port or config["docker"]["default_app_port"],
        force=force,
        dry_run=dry_run,
        yes=yes,
    )

    try:
        if dbt_adapter is not None and not with_dbt:
            raise ValidationError("--dbt-adapter requires --with-dbt")
        _validate_database_options(
            spec, db_port_given=db_port is not None, traefik_domain_given=traefik_domain is not None
        )
        _validate(spec)
        if needs_docker and not docker:
            logging.warning("The selected options need Docker: enabling --docker")
        if spec.db != "none" and not spec.db_password:
            spec.db_password = secrets.token_urlsafe(16)  # before the features read it
        tmpl = apply_features(get_template(spec.template), spec)
        _warn_if_port_in_use(spec)

        if server is not None and not tmpl.servers:
            logging.warning(f"--server is ignored by the '{tmpl.name}' template")
        for notice in tmpl.notices:
            logging.warning(notice)

        _print_summary(spec, tmpl)

        if not spec.yes and not spec.dry_run and not confirm("Proceed?", default=True):
            logging.warning("Aborted by user")
            raise typer.Exit(code=1)

        if spec.dry_run:
            logging.info("Dry run — no changes made")
            return

        outcome = _execute(spec, tmpl)

        _print_next_steps(spec, tmpl, outcome)

    except KickoffError as exc:
        logging.error(str(exc))
        raise typer.Exit(code=1) from exc


def _git_global(key: str) -> str | None:
    if not command_exists("git"):
        return None
    result = run(["git", "config", "--global", key], check=False)
    return result.stdout.strip() or None


def _resolve_author(config: dict[str, Any]) -> tuple[str | None, str | None]:
    """Author name/email: explicit config values win, git fills the gaps."""
    user = config["user"]
    name = user["name"] or None
    email = user["email"] or None
    if user["author_name_from_git"]:
        name = name or _git_global("user.name")
        email = email or _git_global("user.email")
    return name, email


MAX_PORT = 65535


def _validate_database_options(
    spec: ProjectSpec, *, db_port_given: bool, traefik_domain_given: bool = False
) -> None:
    has_db = spec.db != "none"
    if traefik_domain_given and not spec.traefik:
        raise ValidationError("--traefik-domain only applies together with --traefik")
    for flag, used in (
        ("--db-password", spec.db_password is not None),
        ("--expose-db", spec.expose_db),
        ("--with-pgadmin", spec.with_pgadmin),
    ):
        if used and not has_db:
            raise ValidationError(f"{flag} needs a database: add --db postgres or --db postgis")
    if db_port_given and not spec.expose_db:
        raise ValidationError("--db-port only applies together with --expose-db")
    for flag, port in (("--db-port", spec.db_port), ("--app-port", spec.app_port)):
        if not 1 <= port <= MAX_PORT:
            raise ValidationError(f"{flag} must be between 1 and {MAX_PORT}")


def _warn_if_port_in_use(spec: ProjectSpec) -> None:
    """Warn when the database port we are about to publish is already taken locally."""
    if not spec.expose_db:
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        in_use = probe.connect_ex(("127.0.0.1", spec.db_port)) == 0
    if in_use:
        logging.warning(
            f"Port {spec.db_port} is already in use on this machine; "
            "choose another one with --db-port."
        )


def _validate(spec: ProjectSpec) -> None:
    if not re.fullmatch(PROJECT_NAME_PATTERN, spec.name):
        raise ValidationError(
            f"Invalid project name '{spec.name}'. Expected pattern: {PROJECT_NAME_PATTERN}"
        )
    if spec.python_version not in SUPPORTED_PYTHON_VERSIONS:
        raise ValidationError(
            f"Unsupported Python version '{spec.python_version}'. "
            f"Choose one of: {', '.join(SUPPORTED_PYTHON_VERSIONS)}"
        )
    if spec.license not in SUPPORTED_LICENSES:
        raise ValidationError(
            f"Unknown license '{spec.license}'. Choose one of: {', '.join(SUPPORTED_LICENSES)}"
        )
    if spec.server not in SUPPORTED_SERVERS:
        raise ValidationError(
            f"Unknown server '{spec.server}'. Choose one of: {', '.join(SUPPORTED_SERVERS)}"
        )
    if "dbt" in spec.features and spec.dbt_adapter not in ADAPTERS:
        raise ValidationError(
            f"Unknown dbt adapter '{spec.dbt_adapter}'. Choose one of: {', '.join(ADAPTERS)}"
        )
    if spec.db not in SUPPORTED_DATABASES:
        raise ValidationError(
            f"Unknown database '{spec.db}'. Choose one of: {', '.join(SUPPORTED_DATABASES)}"
        )
    if spec.target_dir.exists() and not spec.force:
        raise ValidationError(
            f"Target directory already exists: {spec.target_dir}. Use --force to reuse it."
        )
    if not command_exists("uv"):
        raise ValidationError("`uv` is required but not found on PATH.")


def _github_summary(spec: ProjectSpec) -> str:
    if not spec.create_github:
        return "no"
    visibility = "PRIVATE" if spec.private else "PUBLIC"
    repo = f"{spec.github_owner}/{spec.name}" if spec.github_owner else spec.name
    action = "create and push" if spec.push_initial else "create (no push)"
    return f"yes — will {action} a {visibility} repository '{repo}'"


def _docker_summary(spec: ProjectSpec) -> str:
    if not spec.docker:
        return "no"
    parts = [f"app on port {spec.app_port}"]
    if spec.db != "none":
        parts.append(f"{spec.db} database")
        parts.append(
            f"published on 127.0.0.1:{spec.db_port}" if spec.expose_db else "not published"
        )
    if spec.with_pgadmin:
        parts.append("pgAdmin")
    parts += [name for name in ("redis", "minio", "mail") if getattr(spec, f"with_{name}")]
    if spec.traefik:
        parts.append(f"Traefik (host {spec.name.lower().replace('_', '-')}.{spec.traefik_domain})")
    return "yes — " + ", ".join(parts)


def _print_summary(spec: ProjectSpec, tmpl: TemplateSpec) -> None:
    logging.info(f"Creating project [bold]{spec.name}[/bold]")
    logging.info(f"Template: [bold]{spec.template}[/bold] ({tmpl.description})")
    logging.info(f"Target: {spec.target_dir}")
    logging.info(f"Python: {spec.python_version}")
    logging.info(f"License: {spec.license}")
    if tmpl.servers:
        logging.info(f"Server: {spec.server}")
    if spec.features:
        dbt_note = f" (dbt adapter: {spec.dbt_adapter})" if "dbt" in spec.features else ""
        logging.info(f"Features: {', '.join(spec.features)}{dbt_note}")
    logging.info(f"Branch: {spec.branch}")
    logging.info(f"Git: {'yes' if spec.create_git else 'no'}")
    logging.info(f"GitHub: {_github_summary(spec)}")
    logging.info(f"Docker: {_docker_summary(spec)}")
    logging.info(f"CI: {'yes' if spec.enable_ci else 'no'}")
    logging.info(f"OpenCode: {'yes' if spec.enable_opencode else 'no'}")


def _execute(spec: ProjectSpec, tmpl: TemplateSpec) -> _Outcome:
    """Run every generation step."""
    _prepare_github(spec)
    structure.create_directories(spec, tmpl)
    _run_uv_init(spec, tmpl)
    files.write_base_files(spec, tmpl)
    licenses.write_license(spec)
    pyproject.enrich_pyproject(spec, tmpl)
    _add_dependencies(spec, tmpl)

    if spec.enable_opencode:
        opencode.generate_opencode(spec, tmpl)

    if spec.enable_ci:
        ci.generate_ci(spec, tmpl)

    outcome = _Outcome()
    if spec.create_git and git.init_git(spec):
        outcome.hooks_installed = _install_hooks(spec)
        if spec.create_github:
            outcome.github_created = github.create_repository(spec, tmpl.description)
    return outcome


def _prepare_github(spec: ProjectSpec) -> None:
    """Decide up front whether GitHub is usable, so README badges never link to nothing."""
    if not (spec.create_git and spec.create_github):
        return
    reason = github.unavailable_reason()
    if reason:
        logging.warning(f"{reason} — skipping GitHub repository creation")
        spec.create_github = False
        return
    spec.github_owner = spec.github_owner or github.authenticated_user()


def _run_uv_init(spec: ProjectSpec, tmpl: TemplateSpec) -> None:
    logging.step("Running uv init")
    # --bare: only pyproject.toml (no main.py, README, src/ or .python-version);
    # --vcs none: kickoff runs `git init` itself, and only when asked to;
    # --no-workspace: never register the project in a parent uv workspace.
    run(
        [
            "uv",
            "init",
            "--bare",
            "--vcs",
            "none",
            "--no-workspace",
            "--name",
            spec.name,
            "--python",
            spec.python_version,
            "--description",
            tmpl.description,
            ".",
        ],
        cwd=spec.target_dir,
    )
    logging.success("uv init complete")


def _add_dependencies(spec: ProjectSpec, tmpl: TemplateSpec) -> None:
    logging.step("Adding dependencies")

    prod = production_dependencies(spec, tmpl)
    if prod:
        run(["uv", "add", *prod], cwd=spec.target_dir)
    if tmpl.dev_dependencies:
        run(["uv", "add", "--dev", *tmpl.dev_dependencies], cwd=spec.target_dir)

    logging.success(f"Added {len(prod)} prod and {len(tmpl.dev_dependencies)} dev deps")


def _install_hooks(spec: ProjectSpec) -> bool:
    logging.step("Installing pre-commit hooks")
    try:
        run(["uv", "run", "pre-commit", "install"], cwd=spec.target_dir)
    except ExternalCommandError as exc:
        logging.warning(f"Could not install pre-commit hooks: {exc}")
        return False
    logging.success("pre-commit hooks installed")
    return True


def _print_next_steps(spec: ProjectSpec, tmpl: TemplateSpec, outcome: _Outcome) -> None:
    logging.success("Project created successfully!")
    logging.info(f"Next: cd {spec.name} && uv run ruff check .")
    commands = dict(project_commands(spec, tmpl))
    if "Run server" in commands:
        steps = [commands[label] for label in ("Migrate", "Run server") if label in commands]
        logging.info(f"Run the app: {' && '.join(steps)}")
    if spec.create_git and not outcome.hooks_installed:
        logging.info("Then install the git hooks: uv run pre-commit install")
    if spec.create_github and not outcome.github_created:
        logging.info("The GitHub repository was not created; run `gh repo create` when ready.")
