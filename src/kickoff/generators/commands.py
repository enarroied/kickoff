"""The commands documented in README.md, AGENTS.md and skills."""

from __future__ import annotations

from kickoff.models import ProjectSpec, TemplateSpec

BASE_COMMANDS = (
    ("Install", "uv sync"),
    ("Lint", "uv run ruff check ."),
    ("Format", "uv run ruff format ."),
    ("Test", "uv run pytest"),
    ("Dead code", "uv run vulture"),
    ("Security audit", "uv run pip-audit"),
)


def project_commands(spec: ProjectSpec, template: TemplateSpec) -> list[tuple[str, str]]:
    """Return (label, command) pairs: the shared ones plus the template's own."""
    commands = list(BASE_COMMANDS)
    commands += [
        (label, command.format(package=spec.package_name))
        for label, command in template.commands.items()
    ]
    server = template.servers.get(spec.server)
    if server:
        commands.append(("Run server", server.command.format(package=spec.package_name)))
    return commands
