"""User-defined templates: TOML files in `<config dir>/templates/`.

A custom template extends a built-in one declaratively (no code). Lists and tables in the file
are ADDED to the base template's; `description` replaces it. See the README for the schema.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import replace
from pathlib import Path

from kickoff import config
from kickoff.features import _chain
from kickoff.generators.badges import TOOL_BADGES
from kickoff.generators.ci import CI_STEPS
from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.templates import REGISTRY

NAME_PATTERN = r"^[a-z][a-z0-9-]*$"

# key -> expected TOML type
LIST_KEYS = (
    "dependencies",
    "dev_dependencies",
    "ruff_select_extra",
    "ci_jobs",
    "ignored_directories",
    "gitignore_extra",
    "stack_notes",
    "testing_notes",
    "badges",
)
TABLE_KEYS = ("directories", "commands", "env_vars", "ruff_per_file_ignores", "files")
SCALAR_KEYS = ("description", "extends")
ALLOWED_KEYS = {*LIST_KEYS, *TABLE_KEYS, *SCALAR_KEYS}


class CustomTemplateError(ValueError):
    """The template file is invalid; the message says what to fix."""


def templates_dir() -> Path:
    return config.config_dir() / "templates"


def _check_types(data: dict) -> None:
    unknown = sorted(set(data) - ALLOWED_KEYS)
    if unknown:
        raise CustomTemplateError(
            f"unknown key(s): {', '.join(unknown)}. Allowed: {', '.join(sorted(ALLOWED_KEYS))}"
        )
    for key in LIST_KEYS:
        value = data.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise CustomTemplateError(f"`{key}` must be a list of strings")
    for key in TABLE_KEYS:
        value = data.get(key, {})
        if not isinstance(value, dict):
            raise CustomTemplateError(f"`{key}` must be a table")
    for key in ("directories", "commands", "env_vars", "files"):
        if not all(isinstance(item, str) for item in data.get(key, {}).values()):
            raise CustomTemplateError(f"every value in `{key}` must be a string")
    for pattern, rules in data.get("ruff_per_file_ignores", {}).items():
        if not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules):
            raise CustomTemplateError(
                f"`ruff_per_file_ignores.{pattern}` must be a list of strings"
            )
    for key in SCALAR_KEYS:
        if key in data and not isinstance(data[key], str):
            raise CustomTemplateError(f"`{key}` must be a string")


def _check_references(data: dict) -> None:
    bad_jobs = [job for job in data.get("ci_jobs", []) if job not in CI_STEPS]
    if bad_jobs:
        raise CustomTemplateError(
            f"unknown ci_jobs {bad_jobs}; known: {', '.join(sorted(CI_STEPS))}"
        )
    bad_badges = [key for key in data.get("badges", []) if key not in TOOL_BADGES]
    if bad_badges:
        raise CustomTemplateError(
            f"unknown badges {bad_badges}; known: {', '.join(sorted(TOOL_BADGES))}"
        )


def _files_renderer(files: dict[str, str]):
    def render(spec: ProjectSpec) -> dict[str, str]:
        def fill(text: str) -> str:
            return text.replace("__PACKAGE__", spec.package_name).replace("__NAME__", spec.name)

        return {fill(path): fill(content) for path, content in files.items()}

    return render


def build_template(name: str, data: dict) -> TemplateSpec:
    """Turn parsed TOML into a TemplateSpec (raises CustomTemplateError)."""
    _check_types(data)
    _check_references(data)
    base_name = data.get("extends", "default")
    if base_name not in REGISTRY:
        raise CustomTemplateError(
            f"`extends` must be a built-in template ({', '.join(sorted(REGISTRY))}), "
            f"not '{base_name}'"
        )
    base = REGISTRY[base_name]
    ignores = {
        pattern: list(rules) for pattern, rules in data.get("ruff_per_file_ignores", {}).items()
    }
    return replace(
        base,
        name=name,
        description=data.get("description", base.description),
        directories={**base.directories, **data.get("directories", {})},
        dependencies=[*base.dependencies, *data.get("dependencies", [])],
        dev_dependencies=[*base.dev_dependencies, *data.get("dev_dependencies", [])],
        ruff_select_extra=[*base.ruff_select_extra, *data.get("ruff_select_extra", [])],
        ruff_per_file_ignores={**base.ruff_per_file_ignores, **ignores},
        ci_jobs=[*base.ci_jobs, *data.get("ci_jobs", [])],
        ignored_directories=[*base.ignored_directories, *data.get("ignored_directories", [])],
        gitignore_extra=[*base.gitignore_extra, *data.get("gitignore_extra", [])],
        stack_notes=[*base.stack_notes, *data.get("stack_notes", [])],
        testing_notes=[*base.testing_notes, *data.get("testing_notes", [])],
        badges=[*base.badges, *data.get("badges", [])],
        commands={**base.commands, **data.get("commands", {})},
        env_vars={**base.env_vars, **data.get("env_vars", {})},
        render_files=_chain(base.render_files, _files_renderer(data.get("files", {}))),
    )


def load_custom_templates(
    directory: Path | None = None,
) -> tuple[dict[str, TemplateSpec], dict[str, Path], dict[str, str]]:
    """Return (templates by name, their files, errors by file name). Bad files never raise."""
    directory = directory or templates_dir()
    templates: dict[str, TemplateSpec] = {}
    paths: dict[str, Path] = {}
    errors: dict[str, str] = {}
    if not directory.is_dir():
        return templates, paths, errors
    for path in sorted(directory.glob("*.toml")):
        name = path.stem
        try:
            if not re.fullmatch(NAME_PATTERN, name):
                raise CustomTemplateError(f"file name must match {NAME_PATTERN}")
            if name in REGISTRY:
                raise CustomTemplateError(f"'{name}' is a built-in template; rename the file")
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            templates[name] = build_template(name, data)
            paths[name] = path
        except (CustomTemplateError, tomllib.TOMLDecodeError) as exc:
            errors[path.name] = str(exc)
    return templates, paths, errors
