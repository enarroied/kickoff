""".kickoff.toml: what kickoff generated a project with, so `kickoff add` can extend it.

The file holds options only, never secrets (the database password lives in `.env`).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from kickoff import __version__
from kickoff.exceptions import ValidationError
from kickoff.models import ProjectSpec

MANIFEST_NAME = ".kickoff.toml"

# ProjectSpec fields that are recorded, in file order.
FIELDS = (
    "template",
    "python_version",
    "license",
    "branch",
    "server",
    "features",
    "dbt_adapter",
    "enable_ci",
    "enable_opencode",
    "db",
    "expose_db",
    "db_port",
    "app_port",
    "with_pgadmin",
    "with_redis",
    "with_minio",
    "with_mail",
    "minio_image",
    "traefik",
    "traefik_domain",
    "traefik_network",
    "traefik_entrypoint",
    "traefik_cert_resolver",
)


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_manifest(spec: ProjectSpec) -> str:
    lines = [
        "# Written by kickoff; `kickoff add` reads it. Options only, never secrets.",
        "[kickoff]",
        f"version = {_toml_value(__version__)}",
        "",
        "[project]",
        f"name = {_toml_value(spec.name)}",
    ]
    lines += [f"{field} = {_toml_value(getattr(spec, field))}" for field in FIELDS]
    return "\n".join(lines) + "\n"


def read_manifest(project_dir: Path) -> ProjectSpec:
    """Rebuild the ProjectSpec a project was generated with."""
    path = project_dir / MANIFEST_NAME
    if not path.is_file():
        raise ValidationError(
            f"{path} not found. `kickoff add` only works on projects created with kickoff 0.4 "
            "or later (they contain a .kickoff.toml)."
        )
    data = tomllib.loads(path.read_text(encoding="utf-8")).get("project", {})
    try:
        values = {field: data[field] for field in FIELDS}
        name = data["name"]
    except KeyError as exc:
        raise ValidationError(f"{path} is incomplete: missing {exc}") from exc
    spec = ProjectSpec(name=name, path=project_dir.parent, **values)
    spec.docker = "docker" in spec.features
    return spec
