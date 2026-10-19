"""Which packages `uv add` installs for a project."""

from __future__ import annotations

from kickoff.models import ProjectSpec, TemplateSpec


def production_dependencies(spec: ProjectSpec, template: TemplateSpec) -> list[str]:
    """Template and feature dependencies plus the selected application server."""
    server = template.servers.get(spec.server)
    return [*template.dependencies, *(server.dependencies if server else [])]
