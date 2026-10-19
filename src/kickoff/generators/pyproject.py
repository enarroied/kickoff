"""Enrich pyproject.toml after `uv init --bare`."""

from __future__ import annotations

import tomlkit

from kickoff import defaults
from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.utils import logging


def _to_toml(value: object, package: str) -> object:
    """Convert nested dicts/lists to tomlkit items, substituting `{package}` in strings."""
    if isinstance(value, dict):
        table = tomlkit.table()
        for key, item in value.items():
            table[key] = _to_toml(item, package)
        return table
    if isinstance(value, list):
        return [_to_toml(item, package) for item in value]
    if isinstance(value, str):
        return value.replace("{package}", package)
    return value


def _per_file_ignores(template: TemplateSpec) -> dict[str, list[str]]:
    merged = {pattern: list(rules) for pattern, rules in defaults.RUFF_PER_FILE_IGNORES.items()}
    merged.update(template.ruff_per_file_ignores)
    return merged


def enrich_pyproject(spec: ProjectSpec, template: TemplateSpec) -> None:
    logging.step("Enriching pyproject.toml")

    path = spec.target_dir / "pyproject.toml"
    if not path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {path}")

    doc = tomlkit.parse(path.read_text(encoding="utf-8"))
    package = spec.package_name

    # [project] metadata
    project = doc["project"]
    project["readme"] = "README.md"  # type: ignore[index]
    if spec.license in defaults.LICENSE_SPDX:
        project["license"] = defaults.LICENSE_SPDX[spec.license]  # type: ignore[index]
    if spec.author_name:
        author = tomlkit.inline_table()
        author["name"] = spec.author_name
        if spec.author_email:
            author["email"] = spec.author_email
        authors = tomlkit.array()
        authors.append(author)
        project["authors"] = authors  # type: ignore[index]

    if "tool" not in doc:
        doc["tool"] = tomlkit.table(is_super_table=True)

    # [tool.ruff.lint.per-file-ignores]
    per_file_ignores = tomlkit.table()
    for pattern, rules in _per_file_ignores(template).items():
        per_file_ignores[pattern] = list(rules)

    # [tool.ruff.lint]
    ruff_lint = tomlkit.table()
    ruff_lint["select"] = [*defaults.RUFF_SELECT, *template.ruff_select_extra]
    for key, value in template.ruff_extra.items():
        ruff_lint[key] = _to_toml(value, package)
    ruff_lint["per-file-ignores"] = per_file_ignores

    # [tool.ruff]
    ruff = tomlkit.table()
    ruff["line-length"] = defaults.LINE_LENGTH
    ruff["target-version"] = f"py{spec.python_version.replace('.', '')}"
    ruff["lint"] = ruff_lint
    doc["tool"]["ruff"] = ruff  # type: ignore[index]

    # [tool.vulture]
    vulture = tomlkit.table()
    for key, value in template.vulture_config.items():
        vulture[key] = value
    doc["tool"]["vulture"] = vulture  # type: ignore[index]

    # [tool.pytest.ini_options]
    # The project has no build backend, so tests need src/ on the import path.
    ini_options = tomlkit.table()
    ini_options["testpaths"] = ["tests"]
    ini_options["pythonpath"] = ["src"]
    ini_options["addopts"] = "-ra"
    for key, value in template.pytest_options.items():
        ini_options[key] = _to_toml(value, package)
    pytest = tomlkit.table(is_super_table=True)
    pytest["ini_options"] = ini_options
    doc["tool"]["pytest"] = pytest  # type: ignore[index]

    path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    logging.success("pyproject.toml enriched")
