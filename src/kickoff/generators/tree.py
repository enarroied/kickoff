"""Render directory trees and listings from a template's directory map."""

from __future__ import annotations

from kickoff.models import ProjectSpec, TemplateSpec


def _visible(spec: ProjectSpec, template: TemplateSpec) -> list[tuple[str, str]]:
    """Return (path, comment) for every directory that has a comment."""
    return [
        (f"{pattern.format(package=spec.package_name)}/", comment)
        for pattern, comment in template.directories.items()
        if comment
    ]


def render_tree(spec: ProjectSpec, template: TemplateSpec) -> str:
    """Render an ASCII tree of the documented directories."""
    entries = _visible(spec, template)
    width = max((len(path) for path, _ in entries), default=0)
    lines = [f"{spec.name}/"]
    for index, (path, comment) in enumerate(entries):
        connector = "└──" if index == len(entries) - 1 else "├──"
        lines.append(f"{connector} {path.ljust(width)}  # {comment}")
    return "\n".join(lines)


def render_listing(spec: ProjectSpec, template: TemplateSpec) -> str:
    """Render the documented directories as a Markdown bullet list."""
    return "\n".join(f"- `{path}` — {comment}" for path, comment in _visible(spec, template))
