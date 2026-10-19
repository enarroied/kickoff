"""All templates: the built-in ones plus the user's custom templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kickoff.custom_templates import load_custom_templates
from kickoff.exceptions import ValidationError
from kickoff.models import TemplateSpec
from kickoff.templates import REGISTRY


@dataclass(frozen=True)
class TemplateEntry:
    template: TemplateSpec
    source: str  # "built-in" or the path of the custom file


def all_templates(directory: Path | None = None) -> tuple[dict[str, TemplateEntry], dict[str, str]]:
    """Return (templates by name, errors by custom file name)."""
    entries = {name: TemplateEntry(spec, "built-in") for name, spec in REGISTRY.items()}
    customs, paths, errors = load_custom_templates(directory)
    entries.update({name: TemplateEntry(spec, str(paths[name])) for name, spec in customs.items()})
    return entries, errors


def get_template(name: str, directory: Path | None = None) -> TemplateSpec:
    entries, errors = all_templates(directory)
    if name in entries:
        return entries[name].template
    broken = [file for file in errors if file == f"{name}.toml"]
    if broken:
        raise ValidationError(f"Custom template '{name}' is invalid: {errors[broken[0]]}")
    available = ", ".join(sorted(entries))
    raise ValidationError(f"Unknown template '{name}'. Available: {available}")
