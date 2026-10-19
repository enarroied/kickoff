"""Optional features that can be combined with any template."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from kickoff.features.dbt_feature import dbt_feature
from kickoff.features.docker_feature import docker_feature
from kickoff.features.prefect_feature import prefect_feature
from kickoff.models import FeatureSpec, ProjectSpec, TemplateSpec

# Feature name -> factory. Factories receive the project and the template merged so far,
# because some features depend on options (dbt adapter) or on the template (docker).
# Order matters: docker comes last so it sees everything the other features added.
FEATURES: dict[str, Callable[[ProjectSpec, TemplateSpec], FeatureSpec]] = {
    "prefect": prefect_feature,
    "dbt": dbt_feature,
    "docker": docker_feature,
}


def _chain(
    first: Callable[[ProjectSpec], dict[str, str]],
    second: Callable[[ProjectSpec], dict[str, str]],
) -> Callable[[ProjectSpec], dict[str, str]]:
    def render(spec: ProjectSpec) -> dict[str, str]:
        return {**first(spec), **second(spec)}

    return render


def _merge(template: TemplateSpec, feature: FeatureSpec) -> TemplateSpec:
    return replace(
        template,
        directories={**template.directories, **feature.directories},
        dependencies=[*template.dependencies, *feature.dependencies],
        dev_dependencies=[*template.dev_dependencies, *feature.dev_dependencies],
        gitignore_extra=[*template.gitignore_extra, *feature.gitignore_extra],
        stack_notes=[*template.stack_notes, *feature.stack_notes],
        notices=[*template.notices, *feature.notices],
        env_vars={**template.env_vars, **feature.env_vars},
        env_examples={**template.env_examples, **feature.env_examples},
        testing_notes=[*template.testing_notes, *feature.testing_notes],
        badges=[*template.badges, *feature.badges],
        commands={**template.commands, **feature.commands},
        render_files=_chain(template.render_files, feature.render_files),
    )


def apply_features(template: TemplateSpec, spec: ProjectSpec) -> TemplateSpec:
    """Return the template with every feature selected in `spec.features` merged in."""
    for name in FEATURES:  # fixed order, whatever order the user passed the flags in
        if name in spec.features:
            template = _merge(template, FEATURES[name](spec, template))
    return template
