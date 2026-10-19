"""Generate OpenCode artifacts: AGENTS.md and skills."""

from __future__ import annotations

from kickoff import defaults
from kickoff.generators.commands import project_commands
from kickoff.generators.tree import render_listing, render_tree
from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.utils import logging

AGENTS_MD = """\
# AGENTS.md

## Project

- **Name:** {name}
- **Template:** {template}
- **Description:** {description}

## Stack

{stack}

## Structure

```text
{tree}
```

## Commands

{commands}

## Conventions

- Default branch: `{branch}`
- Commit messages: Conventional Commits
- Configuration lives in environment variables: copy `.env.example` to `.env`, never commit `.env`
- Always run commands through `uv run`
- Run Ruff and Pytest before committing
"""

SKILL_TEMPLATES: dict[str, str] = {
    "project-structure": """\
---
name: project-structure
description: Where to place code in this project
---
# Project Structure

{listing}

Keep new files inside these directories.
""",
    "code-quality": """\
---
name: code-quality
description: Run linting, formatting and dead-code detection
---
# Code Quality

- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Dead code: `uv run vulture`

Fix Ruff violations before committing. Vulture reports at min_confidence={vulture_confidence}.
""",
    "testing": """\
---
name: testing
description: Testing conventions for this project
---
# Testing

- Framework: Pytest
- Run: `uv run pytest`
- Coverage: `uv run pytest --cov=src`
- Place tests under `tests/` mirroring `src/`
- Name test files `test_*.py`, functions `test_*`
{testing_notes}
""",
    "git-workflow": """\
---
name: git-workflow
description: Git conventions for this project
---
# Git Workflow

- Default branch: `{branch}`
- Commit messages: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`)
- Run pre-commit hooks before pushing
- Never commit secrets or `.env`
""",
}


def _stack_lines(spec: ProjectSpec, template: TemplateSpec) -> list[str]:
    base = [
        f"Python {spec.python_version}",
        "Dependency management: `uv`",
        "Linting/formatting: Ruff",
        "Dead code detection: Vulture",
        "Testing: Pytest",
        "Pre-commit hooks: pre-commit",
    ]
    notes = [
        note.format(server=spec.server, package=spec.package_name) for note in template.stack_notes
    ]
    return [f"- {line}" for line in [*base, *notes]]


def _context(spec: ProjectSpec, template: TemplateSpec) -> dict[str, str]:
    """Every value that can appear in AGENTS.md or a skill, resolved once."""
    confidence = template.vulture_config.get("min_confidence", defaults.VULTURE_MIN_CONFIDENCE)
    commands = "\n".join(f"- {label}: `{cmd}`" for label, cmd in project_commands(spec, template))
    return {
        "name": spec.name,
        "template": template.name,
        "description": template.description,
        "python_version": spec.python_version,
        "package": spec.package_name,
        "branch": spec.branch,
        "tree": render_tree(spec, template),
        "listing": render_listing(spec, template),
        "stack": "\n".join(_stack_lines(spec, template)),
        "commands": commands,
        "vulture_confidence": str(confidence),
        "testing_notes": "\n".join(f"- {note}" for note in template.testing_notes),
    }


def generate_opencode(spec: ProjectSpec, template: TemplateSpec) -> None:
    logging.step("Generating OpenCode artifacts")

    root = spec.target_dir
    context = _context(spec, template)

    (root / "AGENTS.md").write_text(AGENTS_MD.format(**context), encoding="utf-8")

    for skill in template.opencode_skills:
        skill_dir = root / ".opencode" / "skills" / skill
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = SKILL_TEMPLATES.get(skill, f"# {skill}\n")
        (skill_dir / "SKILL.md").write_text(
            content.format(**context).rstrip() + "\n", encoding="utf-8"
        )

    logging.success(f"Generated AGENTS.md and {len(template.opencode_skills)} skills")
