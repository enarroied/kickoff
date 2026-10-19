"""Data models for kickoff."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from kickoff import defaults


@dataclass
class ProjectSpec:
    """User-provided and resolved parameters for a new project."""

    name: str
    path: Path
    template: str = defaults.DEFAULT_TEMPLATE_NAME
    python_version: str = defaults.DEFAULT_PYTHON_VERSION
    license: str = defaults.DEFAULT_LICENSE
    branch: str = defaults.DEFAULT_BRANCH
    server: str = defaults.DEFAULT_SERVER
    features: list[str] = field(default_factory=list)
    dbt_adapter: str = defaults.DEFAULT_DBT_ADAPTER
    author_name: str | None = None
    author_email: str | None = None
    github_owner: str | None = None
    private: bool = False
    create_git: bool = True
    create_github: bool = True
    push_initial: bool = True
    enable_ci: bool = True
    enable_opencode: bool = True
    docker: bool = False
    db: str = defaults.DEFAULT_DATABASE
    db_password: str | None = None
    expose_db: bool = False
    with_pgadmin: bool = False
    with_redis: bool = False
    with_minio: bool = False
    with_mail: bool = False
    minio_image: str = defaults.MINIO_IMAGE
    traefik: bool = False
    traefik_domain: str = defaults.DEFAULT_TRAEFIK_DOMAIN
    traefik_network: str = defaults.DEFAULT_TRAEFIK_NETWORK
    traefik_entrypoint: str = defaults.DEFAULT_TRAEFIK_ENTRYPOINT
    traefik_cert_resolver: str = defaults.DEFAULT_TRAEFIK_CERT_RESOLVER
    db_port: int = defaults.DEFAULT_DB_PORT
    app_port: int = defaults.DEFAULT_APP_PORT
    force: bool = False
    dry_run: bool = False
    yes: bool = False

    @property
    def target_dir(self) -> Path:
        return self.path / self.name

    @property
    def public_repo(self) -> bool:
        """True when a public, pushed GitHub repository will exist (badges can link to it)."""
        return (
            self.create_git
            and self.create_github
            and self.push_initial
            and not self.private
            and self.github_owner is not None
        )

    @property
    def package_name(self) -> str:
        return self.name.replace("-", "_").lower()


@dataclass
class DockerConfig:
    """How a template runs inside a container (used by the docker feature).

    ``command`` is the container's CMD in exec form; ``{package}`` and ``{port}`` are
    substituted. ``dev_command`` replaces it in compose.override.yml (for example with reload).
    ``entrypoint_steps`` are shell commands run before the CMD on every start.
    """

    container_port: int = 8000
    command: list[str] = field(default_factory=lambda: ["python", "-m", "{package}"])
    dev_command: list[str] | None = None
    healthcheck_path: str | None = None
    entrypoint_steps: list[str] = field(default_factory=list)
    system_packages: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    main_module: bool = False  # generate src/<package>/__main__.py (needed by `python -m`)


@dataclass
class ServerSpec:
    """An application server a template can be run with."""

    dependencies: list[str]
    command: str  # may contain {package}
    docker_command: list[str] = field(default_factory=list)  # container CMD, see DockerConfig
    docker_dev_command: list[str] | None = None


def _no_files(_spec: ProjectSpec) -> dict[str, str]:
    return {}


@dataclass
class FeatureSpec:
    """An optional capability (Prefect, dbt, ...) that is merged into any template.

    Every field is added to the template's own value of the same name, see
    ``kickoff.features.apply_features``.
    """

    name: str
    directories: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    dev_dependencies: list[str] = field(default_factory=list)
    gitignore_extra: list[str] = field(default_factory=list)
    stack_notes: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
    badges: list[str] = field(default_factory=list)
    commands: dict[str, str] = field(default_factory=dict)
    env_examples: dict[str, str] = field(default_factory=dict)
    testing_notes: list[str] = field(default_factory=list)
    render_files: Callable[[ProjectSpec], dict[str, str]] = _no_files


@dataclass
class TemplateSpec:
    """Defines everything a template contributes to a generated project.

    ``directories`` maps a directory pattern (``{package}`` is substituted) to a
    short comment. Directories with a comment are listed in the generated trees
    (README, AGENTS.md, skills); directories with an empty comment are created
    but not listed. Everything else (gitkeep files, .gitignore sections, docs)
    is derived from this one mapping.

    ``render_files`` returns extra files (relative path -> content) that depend
    on the project, for example the Django project skeleton.
    """

    name: str
    description: str
    directories: dict[str, str]
    dependencies: list[str]
    dev_dependencies: list[str]
    ruff_select_extra: list[str] = field(default_factory=list)
    ruff_per_file_ignores: dict[str, list[str]] = field(default_factory=dict)
    ruff_extra: dict = field(default_factory=dict)
    pytest_options: dict = field(default_factory=dict)
    vulture_config: dict = field(default_factory=dict)
    ci_jobs: list[str] = field(default_factory=list)
    opencode_skills: list[str] = field(default_factory=list)
    ignored_directories: list[str] = field(default_factory=list)
    gitignore_extra: list[str] = field(default_factory=list)
    stack_notes: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
    env_examples: dict[str, str] = field(default_factory=dict)
    testing_notes: list[str] = field(default_factory=list)
    ci_step_overrides: dict[str, str] = field(default_factory=dict)
    db_aware: bool = False  # the app itself reads POSTGRES_* variables (Django)
    badges: list[str] = field(default_factory=list)
    commands: dict[str, str] = field(default_factory=dict)
    servers: dict[str, ServerSpec] = field(default_factory=dict)
    render_files: Callable[[ProjectSpec], dict[str, str]] = _no_files
    docker_config: DockerConfig = field(default_factory=DockerConfig)
