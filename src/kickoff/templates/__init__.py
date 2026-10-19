"""Template registry."""

from __future__ import annotations

from kickoff.exceptions import ValidationError
from kickoff.models import TemplateSpec
from kickoff.templates.default_template import DEFAULT_TEMPLATE
from kickoff.templates.django_template import DJANGO_TEMPLATE
from kickoff.templates.jupyter_template import JUPYTER_TEMPLATE

REGISTRY: dict[str, TemplateSpec] = {
    DEFAULT_TEMPLATE.name: DEFAULT_TEMPLATE,
    DJANGO_TEMPLATE.name: DJANGO_TEMPLATE,
    JUPYTER_TEMPLATE.name: JUPYTER_TEMPLATE,
}


def get_template(name: str) -> TemplateSpec:
    if name not in REGISTRY:
        available = ", ".join(sorted(REGISTRY))
        raise ValidationError(f"Unknown template '{name}'. Available: {available}")
    return REGISTRY[name]


def list_templates() -> list[TemplateSpec]:
    return list(REGISTRY.values())
