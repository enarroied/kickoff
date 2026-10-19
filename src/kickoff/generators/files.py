"""Write base files for a new project."""

from __future__ import annotations

import secrets
from pathlib import Path

from kickoff import defaults
from kickoff.generators.badges import render_badges
from kickoff.generators.commands import project_commands
from kickoff.generators.tree import render_tree
from kickoff.manifest import MANIFEST_NAME, render_manifest
from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.utils import logging

GITIGNORE_BASE = """\
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.venv/
venv/
.env
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
.DS_Store
.idea/
.vscode/
"""

GITIGNORE_DIRECTORY = """
# {directory}/ (directories are kept through .gitkeep files)
{directory}/**
!{directory}/**/
!{directory}/**/.gitkeep
"""

README_TEMPLATE = """\
# {name}

{badges}

{description}

## Setup

```bash
{setup}
```

## Development

```bash
{commands}
```

## Structure

```text
{tree}
```
"""

SMOKE_TEST = '''\
"""Smoke test: the package can be imported."""

import {package}


def test_package_imports() -> None:
    assert {package}.__doc__
'''


def render_gitignore(template: TemplateSpec) -> str:
    """Build .gitignore; optional sections follow the template's directories."""
    parts = [GITIGNORE_BASE]
    parts += [GITIGNORE_DIRECTORY.format(directory=d) for d in template.ignored_directories]
    if template.gitignore_extra:
        parts.append("\n# Template specific\n" + "\n".join(template.gitignore_extra) + "\n")
    return "".join(parts)


def render_setup(template: TemplateSpec) -> str:
    """Setup commands for the README; `.env` only matters when the template defines variables."""
    steps = ["uv sync"]
    if template.env_vars:
        steps.append("cp .env.example .env  # then edit the values")
    steps.append("uv run pre-commit install")
    return "\n".join(steps)


def render_env(template: TemplateSpec, *, example: bool) -> str:
    """Content of `.env` (real values, secrets generated) or `.env.example` (placeholders)."""
    lines = ["# Environment variables. Never commit .env; keep .env.example up to date."]
    for name, value in template.env_vars.items():
        if example and name in template.env_examples:
            value = template.env_examples[name]
        elif value == defaults.ENV_SECRET:
            value = "change-me" if example else secrets.token_urlsafe(50)
        lines.append(f"{name}={value}")
    return "\n".join(lines) + "\n"


def render_dev_commands(spec: ProjectSpec, template: TemplateSpec) -> str:
    """Commands for the README's development block (everything except `uv sync`)."""
    commands = [(label, cmd) for label, cmd in project_commands(spec, template) if cmd != "uv sync"]
    width = max(len(cmd) for _, cmd in commands)
    return "\n".join(f"{cmd.ljust(width)}  # {label}" for label, cmd in commands)


def render_precommit() -> str:
    """Ruff runs through `uv run`, so hooks always use the project's own Ruff version."""
    return f"""\
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: uv run ruff check --fix
        language: system
        types_or: [python, pyi]
        require_serial: true
      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types_or: [python, pyi]
        require_serial: true

  - repo: {defaults.PRECOMMIT_HOOKS_REPO}
    rev: {defaults.PRECOMMIT_HOOKS_REV}
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
"""


def write_base_files(spec: ProjectSpec, template: TemplateSpec) -> None:
    logging.step("Writing base files")

    root = spec.target_dir

    _write(root / ".gitignore", render_gitignore(template))
    _write(
        root / "README.md",
        README_TEMPLATE.format(
            name=spec.name,
            description=template.description,
            tree=render_tree(spec, template),
            badges="\n".join(render_badges(spec, template)),
            setup=render_setup(template),
            commands=render_dev_commands(spec, template),
        ),
    )
    _write(root / ".pre-commit-config.yaml", render_precommit())
    _write(root / ".python-version", f"{spec.python_version}\n")
    _write(root / ".env", render_env(template, example=False))
    _write(root / ".env.example", render_env(template, example=True))
    _write(root / MANIFEST_NAME, render_manifest(spec))

    # Package and tests
    _write(root / "src" / spec.package_name / "__init__.py", f'"""{spec.name} package."""\n')
    _write(root / "tests" / "__init__.py", "")
    _write(
        root / "tests" / "test_smoke.py",
        SMOKE_TEST.format(package=spec.package_name),
    )

    # Template-specific files (for example the Django skeleton)
    for relative, content in template.render_files(spec).items():
        _write(root / relative, content)

    # Keep every empty directory in git
    for pattern in template.directories:
        directory = root / pattern.format(package=spec.package_name)
        if not any(directory.iterdir()):
            _write(directory / ".gitkeep", "")

    logging.success("Base files written")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
