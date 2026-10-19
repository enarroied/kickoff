"""The 'default' template — generic Python projects."""

from __future__ import annotations

from kickoff import defaults
from kickoff.models import DockerConfig, TemplateSpec

DEFAULT_TEMPLATE = TemplateSpec(
    name=defaults.DEFAULT_TEMPLATE_NAME,
    description="Generic Python project (data engineering, scripts, libraries)",
    directories={
        "src/{package}": "source code",
        "tests": "tests",
        "docs": "documentation",
        "img": "images and diagrams",
        "scripts": "utility scripts",
        "data": "local data (gitignored)",
        "data/raw": "",
        "data/interim": "",
        "data/processed": "",
    },
    # No version pins: `uv add` resolves the latest release and records it.
    dependencies=["typer"],
    dev_dependencies=["ruff", "vulture", "pytest", "pytest-cov", "pre-commit", "pip-audit"],
    ruff_extra={},
    vulture_config={
        "min_confidence": defaults.VULTURE_MIN_CONFIDENCE,
        "paths": ["src"],
        "sort_by_size": True,
    },
    ignored_directories=["data"],
    docker_config=DockerConfig(main_module=True),
    ci_jobs=["lint", "format", "test", "vulture"],
    opencode_skills=[
        "project-structure",
        "code-quality",
        "testing",
        "git-workflow",
    ],
)
