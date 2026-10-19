"""Generate the GitHub Actions CI workflow."""

from __future__ import annotations

from dataclasses import dataclass

from kickoff import defaults
from kickoff.features.database import has_database
from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.templates.jupyter_files import NBVAL_COMMAND
from kickoff.utils import logging

# Maps a template's `ci_jobs` entry to a workflow step (name, command).
CI_STEPS: dict[str, tuple[str, str]] = {
    "lint": ("Lint", "uv run ruff check ."),
    "format": ("Format check", "uv run ruff format --check ."),
    "test": ("Test", "uv run pytest"),
    "vulture": ("Dead code", "uv run vulture"),
    "notebooks": ("Notebooks", NBVAL_COMMAND),
    # Django: `check --deploy` only fails on errors, deployment warnings are informational.
    "django-check": ("Django system check", "uv run python manage.py check --deploy"),
    "django-migrations": (
        "Check for missing migrations",
        "uv run python manage.py makemigrations --check --dry-run",
    ),
}


SECURITY_CRON = "0 0 * * 1"  # every Monday at midnight (UTC)
SECURITY_COMMAND = "uv run pip-audit"


CI_DB_PASSWORD = "postgres"  # throwaway database of the CI job, not a secret


@dataclass(frozen=True)
class CiDatabase:
    """A PostgreSQL service for the test job (templates whose app reads POSTGRES_*)."""

    image: str
    user: str
    name: str
    postgis: bool


def _database_lines(database: CiDatabase) -> list[str]:
    env = {
        "POSTGRES_USER": database.user,
        "POSTGRES_PASSWORD": CI_DB_PASSWORD,
        "POSTGRES_DB": database.name,
    }
    return [
        "    services:",
        "      postgres:",
        f"        image: {database.image}",
        "        env:",
        *[f"          {key}: {value}" for key, value in env.items()],
        "        ports:",
        "          - 5432:5432",
        "        options: >-",
        f'          --health-cmd "pg_isready -U {database.user}"',
        "          --health-interval 10s",
        "          --health-timeout 5s",
        "          --health-retries 5",
        "    env:",
        "      POSTGRES_HOST: localhost",
        '      POSTGRES_PORT: "5432"',
        *[f"      {key}: {value}" for key, value in env.items()],
    ]


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def python_matrix(python_version: str) -> list[str]:
    """Supported Python versions from the project's own version upwards."""
    minimum = _version_key(python_version)
    return [v for v in defaults.SUPPORTED_PYTHON_VERSIONS if _version_key(v) >= minimum]


def render_ci(
    branch: str,
    python_versions: list[str],
    ci_jobs: list[str],
    step_overrides: dict[str, str] | None = None,
    database: CiDatabase | None = None,
) -> str:
    versions = ", ".join(f'"{v}"' for v in python_versions)
    lines = [
        "name: CI",
        "",
        "on:",
        "  push:",
        f"    branches: [{branch}]",
        "  pull_request:",
        f"    branches: [{branch}]",
        "",
        "permissions:",
        "  contents: read",
        "",
        "jobs:",
        "  quality:",
        "    runs-on: ubuntu-latest",
        "    strategy:",
        "      fail-fast: false",
        "      matrix:",
        f"        python-version: [{versions}]",
        *(_database_lines(database) if database else []),
        "    steps:",
        f"      - uses: {defaults.ACTION_CHECKOUT}",
        "      - name: Install uv",
        f"        uses: {defaults.ACTION_SETUP_UV}",
        "        with:",
        "          python-version: ${{ matrix.python-version }}",
        "          enable-cache: true",
        *(
            [
                "      - name: Install GDAL",
                "        run: sudo apt-get update && sudo apt-get install -y gdal-bin libgdal-dev",
            ]
            if database and database.postgis
            else []
        ),
        "      - name: Install dependencies",
        "        run: uv sync --all-groups",
    ]
    overrides = step_overrides or {}
    for job in ci_jobs:
        step_name, default_command = CI_STEPS[job]
        command = overrides.get(job, default_command)
        lines += [f"      - name: {step_name}", f"        run: {command}"]
    return "\n".join(lines) + "\n"


def render_security(python_version: str) -> str:
    """Weekly dependency audit, kept out of ci.yml so new advisories never block a PR."""
    lines = [
        "name: Security",
        "",
        "on:",
        "  schedule:",
        f"    - cron: '{SECURITY_CRON}'",
        "  workflow_dispatch:",
        "",
        "permissions:",
        "  contents: read",
        "",
        "jobs:",
        "  security:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        f"      - uses: {defaults.ACTION_CHECKOUT}",
        "      - name: Install uv",
        f"        uses: {defaults.ACTION_SETUP_UV}",
        "        with:",
        f'          python-version: "{python_version}"',
        "          enable-cache: true",
        "      - name: Install dependencies",
        "        run: uv sync --all-groups",
        "      - name: Security audit (pip-audit)",
        f"        run: {SECURITY_COMMAND}",
    ]
    return "\n".join(lines) + "\n"


def generate_ci(spec: ProjectSpec, template: TemplateSpec) -> None:
    logging.step("Generating GitHub Actions workflows")

    workflow_dir = spec.target_dir / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)

    database = None
    if template.db_aware and has_database(spec):
        database = CiDatabase(
            image=defaults.DB_IMAGES[spec.db],
            user=spec.package_name,
            name=spec.package_name,
            postgis=spec.db == "postgis",
        )
    content = render_ci(
        spec.branch,
        python_matrix(spec.python_version),
        template.ci_jobs,
        template.ci_step_overrides,
        database,
    )
    (workflow_dir / "ci.yml").write_text(content, encoding="utf-8")
    (workflow_dir / "security.yml").write_text(
        render_security(spec.python_version), encoding="utf-8"
    )

    logging.success("CI and security workflows generated")
