"""`kickoff add`: extend a project created by kickoff with another feature.

The plan is computed without touching the project. Existing files are never silently
overwritten: a file is replaced only when it still equals what kickoff generated before; any
other difference is written next to it as `<name>.kickoff-new` for you to merge.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field, replace
from pathlib import Path

from kickoff import defaults
from kickoff.dependencies import production_dependencies
from kickoff.exceptions import ValidationError
from kickoff.features import apply_features
from kickoff.features.dbt_adapters import ADAPTERS
from kickoff.generators.badges import TOOL_BADGES, _tool_badge
from kickoff.generators.files import render_gitignore
from kickoff.manifest import MANIFEST_NAME, read_manifest, render_manifest
from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.registry import get_template

FEATURE_CHOICES = ("prefect", "dbt", "docker", "pgadmin", "redis", "minio", "mail", "traefik")
SUFFIX = ".kickoff-new"


@dataclass
class AddPlan:
    feature: str
    old_spec: ProjectSpec
    new_spec: ProjectSpec
    new_template: TemplateSpec
    create: dict[str, str] = field(default_factory=dict)
    overwrite: dict[str, str] = field(default_factory=dict)
    conflicts: dict[str, str] = field(default_factory=dict)
    directories: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    dev_dependencies: list[str] = field(default_factory=list)
    env_added: dict[str, str] = field(default_factory=dict)
    env_example_added: dict[str, str] = field(default_factory=dict)
    env_changed: dict[str, str] = field(default_factory=dict)
    gitignore_lines: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    commands: dict[str, str] = field(default_factory=dict)


def _ensure_docker(spec: ProjectSpec) -> None:
    if "docker" not in spec.features:
        spec.features.append("docker")
    spec.docker = True


FLAGS = {
    "pgadmin": "with_pgadmin",
    "redis": "with_redis",
    "minio": "with_minio",
    "mail": "with_mail",
    "traefik": "traefik",
}


def _is_present(spec: ProjectSpec, feature: str) -> bool:
    if feature in ("prefect", "dbt", "docker"):
        return feature in spec.features
    return bool(getattr(spec, FLAGS[feature]))


def apply_feature(
    old: ProjectSpec,
    feature: str,
    *,
    dbt_adapter: str | None = None,
    traefik_domain: str | None = None,
) -> ProjectSpec:
    """Return a copy of `old` with `feature` switched on."""
    if feature not in FEATURE_CHOICES:
        choices = ", ".join(FEATURE_CHOICES)
        raise ValidationError(f"Unknown feature '{feature}'. Choose one of: {choices}")
    spec = replace(old, features=list(old.features))
    if _is_present(spec, feature):
        raise ValidationError(f"'{feature}' is already part of this project.")
    if feature == "dbt":
        if dbt_adapter is not None and dbt_adapter not in ADAPTERS:
            adapters = ", ".join(ADAPTERS)
            raise ValidationError(f"Unknown dbt adapter '{dbt_adapter}'. Choose one of: {adapters}")
        spec.features.append("dbt")
        spec.dbt_adapter = dbt_adapter or spec.dbt_adapter
    elif feature == "prefect":
        spec.features.append("prefect")
    elif feature == "docker":
        _ensure_docker(spec)
    else:
        if feature == "pgadmin" and spec.db == "none":
            raise ValidationError("pgadmin needs a database; this project has none.")
        setattr(spec, FLAGS[feature], True)
        _ensure_docker(spec)
        if feature == "traefik" and traefik_domain:
            spec.traefik_domain = traefik_domain
    return spec


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    pairs = (
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    return {key.strip(): value for key, value in pairs}


def _resolve(spec: ProjectSpec) -> TemplateSpec:
    return apply_features(get_template(spec.template), spec)


def build_plan(
    project_dir: Path,
    feature: str,
    *,
    dbt_adapter: str | None = None,
    traefik_domain: str | None = None,
) -> AddPlan:
    old = read_manifest(project_dir)
    env = read_env(project_dir / ".env")
    old.db_password = env.get("POSTGRES_PASSWORD")  # keeps dbt/db values aligned
    new = apply_feature(old, feature, dbt_adapter=dbt_adapter, traefik_domain=traefik_domain)
    old_template, new_template = _resolve(old), _resolve(new)
    plan = AddPlan(feature, old, new, new_template)

    old_files = old_template.render_files(old)
    for relative, content in new_template.render_files(new).items():
        target = project_dir / relative
        if not target.exists():
            plan.create[relative] = content
            continue
        current = target.read_text(encoding="utf-8")
        if current == content or content == old_files.get(relative):
            continue  # already up to date, or the feature does not change this file
        if current == old_files.get(relative):
            plan.overwrite[relative] = content
        else:
            plan.conflicts[relative] = content

    plan.directories = [d for d in new_template.directories if d not in old_template.directories]
    plan.dependencies = [
        dep
        for dep in production_dependencies(new, new_template)
        if dep not in production_dependencies(old, old_template)
    ]
    plan.dev_dependencies = [
        dep for dep in new_template.dev_dependencies if dep not in old_template.dev_dependencies
    ]

    example = read_env(project_dir / ".env.example")
    for name, value in new_template.env_vars.items():
        shown = new_template.env_examples.get(name, value)
        if value == defaults.ENV_SECRET:
            value, shown = secrets.token_urlsafe(50), "change-me"
        if name not in env:
            plan.env_added[name] = value
        elif old_template.env_vars.get(name) != new_template.env_vars[name]:
            plan.env_changed[name] = value
        if name not in example:
            plan.env_example_added[name] = shown

    gitignore = project_dir / ".gitignore"
    existing_ignore = []
    if gitignore.is_file():
        existing_ignore = gitignore.read_text(encoding="utf-8").splitlines()
    old_lines = set(render_gitignore(old_template).splitlines())
    plan.gitignore_lines = [
        line
        for line in render_gitignore(new_template).splitlines()
        if line.strip() and line not in old_lines and line not in existing_ignore
    ]

    plan.notices = [n for n in new_template.notices if n not in old_template.notices]
    new_keys = [k for k in dict.fromkeys(new_template.badges) if k not in old_template.badges]
    plan.badges = [_tool_badge(TOOL_BADGES[key]) for key in new_keys]
    plan.commands = {
        label: command
        for label, command in new_template.commands.items()
        if label not in old_template.commands
    }
    return plan


def _append(path: Path, lines: list[str]) -> None:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n".join(lines) + "\n", encoding="utf-8")


def write_plan(project_dir: Path, plan: AddPlan) -> None:
    """Apply everything except `uv add` (the caller runs it, then calls write_manifest)."""
    for directory in plan.directories:
        (project_dir / directory.format(package=plan.new_spec.package_name)).mkdir(
            parents=True, exist_ok=True
        )
    for relative, content in {**plan.create, **plan.overwrite}.items():
        target = project_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    for relative, content in plan.conflicts.items():
        (project_dir / (relative + SUFFIX)).write_text(content, encoding="utf-8")
    for directory in plan.directories:
        path = project_dir / directory.format(package=plan.new_spec.package_name)
        if path.is_dir() and not any(path.iterdir()):
            (path / ".gitkeep").write_text("", encoding="utf-8")
    if plan.env_added:
        _append(project_dir / ".env", [f"{k}={v}" for k, v in plan.env_added.items()])
    if plan.env_example_added:
        lines = [f"{k}={v}" for k, v in plan.env_example_added.items()]
        _append(project_dir / ".env.example", lines)
    if plan.gitignore_lines:
        header = ["", f"# Added by kickoff add {plan.feature}"]
        _append(project_dir / ".gitignore", [*header, *plan.gitignore_lines])


def write_manifest(project_dir: Path, plan: AddPlan) -> None:
    (project_dir / MANIFEST_NAME).write_text(render_manifest(plan.new_spec), encoding="utf-8")
