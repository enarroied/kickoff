"""Create the directory tree for a new project."""

from __future__ import annotations

from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.utils import logging


def create_directories(spec: ProjectSpec, template: TemplateSpec) -> None:
    logging.step("Creating directory structure")

    spec.target_dir.mkdir(parents=True, exist_ok=spec.force)

    for pattern in template.directories:
        relative = pattern.format(package=spec.package_name)
        (spec.target_dir / relative).mkdir(parents=True, exist_ok=True)

    logging.success(f"Created {len(template.directories)} directories")
