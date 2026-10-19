"""README badges, chosen from what the generated project actually contains."""

from __future__ import annotations

from dataclasses import dataclass

from kickoff.models import ProjectSpec, TemplateSpec

SHIELDS = "https://img.shields.io"
RAW = "https://raw.githubusercontent.com"
# Official endpoint badges published by Astral.
RUFF_BADGE = f"{SHIELDS}/endpoint?url={RAW}/astral-sh/ruff/main/assets/badge/v2.json"
UV_BADGE = f"{SHIELDS}/endpoint?url={RAW}/astral-sh/uv/main/assets/badge/v0.json"


@dataclass(frozen=True)
class ToolBadge:
    """A static badge for a tool or framework a template or feature uses."""

    label: str
    color: str
    logo: str | None = None
    logo_color: str = "white"


# Keys are referenced by `TemplateSpec.badges`. New tools: add one entry here.
TOOL_BADGES: dict[str, ToolBadge] = {
    "django": ToolBadge("Django", "092E20", "django"),
    "prefect": ToolBadge("Prefect", "F02D5E", "prefect"),
    "dbt": ToolBadge("dbt", "FF694B"),  # dbt has no logo on shields.io
    "duckdb": ToolBadge("DuckDB", "FFF", "duckdb", "374151"),
    "postgresql": ToolBadge("PostgreSQL", "4169E1", "postgresql"),
    "sqlite": ToolBadge("SQLite", "003B57", "sqlite"),
    "postgis": ToolBadge("PostGIS", "336791", "postgresql"),
    "docker": ToolBadge("Docker", "2496ED", "docker"),
    "redis": ToolBadge("Redis", "DC382D", "redis"),
    "minio": ToolBadge("MinIO", "C5A572"),  # no logo, as in the shields.io example
    "mailpit": ToolBadge("Mailpit", "475569"),
    "traefik": ToolBadge("Traefik", "24A1C1", "traefikproxy"),
    "jupyter": ToolBadge("Jupyter", "F37626", "jupyter"),
    "polars": ToolBadge("Polars", "0075FF", "polars"),
}


def _escape(text: str) -> str:
    """Escape a value for a shields.io static badge path."""
    return text.replace("-", "--").replace("_", "__").replace(" ", "_")


def _tool_badge(badge: ToolBadge) -> str:
    url = f"{SHIELDS}/badge/{_escape(badge.label)}-{badge.color}"
    if badge.logo:
        url += f"?logo={badge.logo}&logoColor={badge.logo_color}"
    return f"![{badge.label}]({url})"


def _python_badge(spec: ProjectSpec) -> str:
    if spec.public_repo:
        # Reads requires-python from pyproject.toml, so it never goes stale.
        raw = f"{RAW}/{spec.github_owner}/{spec.name}/{spec.branch}/pyproject.toml"
        url = (
            f"{SHIELDS}/badge/dynamic/toml?url={raw}"
            "&query=$.project.requires-python&label=Python&logo=python&logoColor=white"
        )
    else:
        url = f"{SHIELDS}/badge/Python-{spec.python_version}+-3776AB?logo=python&logoColor=white"
    return f"![Python]({url})"


def _workflow_badge(spec: ProjectSpec, workflow: str, label: str) -> str:
    base = f"https://github.com/{spec.github_owner}/{spec.name}/actions/workflows/{workflow}"
    return f"[![{label}]({base}/badge.svg)]({base})"


def _license_badge(spec: ProjectSpec) -> str | None:
    if spec.license == "none":
        return None
    if spec.public_repo:
        return f"![License]({SHIELDS}/github/license/{spec.github_owner}/{spec.name})"
    return f"![License]({SHIELDS}/badge/License-{_escape(spec.license)}-blue)"


def render_badges(spec: ProjectSpec, template: TemplateSpec) -> list[str]:
    """Return the badges as Markdown, in display order.

    Repository-bound badges (CI, security, dynamic Python/License) are only
    included when a public, pushed GitHub repository will exist; otherwise they
    would be broken links.
    """
    badges = [_python_badge(spec)]
    if spec.public_repo and spec.enable_ci:
        badges.append(_workflow_badge(spec, "ci.yml", "CI"))
        badges.append(_workflow_badge(spec, "security.yml", "Security"))
    badges += [f"![Ruff]({RUFF_BADGE})", f"![uv]({UV_BADGE})"]
    badges += [_tool_badge(TOOL_BADGES[key]) for key in dict.fromkeys(template.badges)]
    license_badge = _license_badge(spec)
    if license_badge:
        badges.append(license_badge)
    return badges
