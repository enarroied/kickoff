"""The `--with-prefect` feature: an example flow and a prefect.yaml."""

from __future__ import annotations

from kickoff.models import FeatureSpec, ProjectSpec, TemplateSpec

FLOWS_INIT_PY = '"""Prefect flows."""\n'

HELLO_FLOW_PY = '''\
"""Example Prefect flow. Replace it with your own flows."""

from prefect import flow, task


def make_greeting(name: str) -> str:
    """Build the greeting (a plain function, easy to unit test)."""
    return f"Hello, {name}!"


@task
def greet(name: str) -> str:
    """Task wrapping the greeting."""
    return make_greeting(name)


@flow(log_prints=True)
def hello_flow(name: str = "world") -> str:
    """Greet someone."""
    message = greet(name)
    print(message)
    return message


if __name__ == "__main__":
    hello_flow()
'''

# `prefect deploy --all` reads this file. `pull: null` makes Prefect ask how workers should
# get the code the first time you deploy (local directory, git clone, ...).
PREFECT_YAML = """\
name: __NAME__
prefect-version: null

build: null
push: null
pull: null

deployments:
  - name: hello
    entrypoint: src/__PACKAGE__/flows/hello.py:hello_flow
    work_pool:
      name: default
"""

PREFECTIGNORE = """\
# Files Prefect skips when it packages a deployment.
.git/
.venv/
__pycache__/
*.py[cod]
.env
.ruff_cache/
.pytest_cache/
"""

FLOW_TEST_PY = '''\
"""Tests for the Prefect flows: pure functions only, no Prefect server needed."""

from __PACKAGE__.flows.hello import make_greeting


def test_make_greeting() -> None:
    assert make_greeting("kickoff") == "Hello, kickoff!"
'''


def prefect_feature(spec: ProjectSpec, _template: TemplateSpec) -> FeatureSpec:
    package = spec.package_name

    def render_files(_spec: ProjectSpec) -> dict[str, str]:
        files = {
            f"src/{package}/flows/__init__.py": FLOWS_INIT_PY,
            f"src/{package}/flows/hello.py": HELLO_FLOW_PY,
            "prefect.yaml": PREFECT_YAML,
            ".prefectignore": PREFECTIGNORE,
            "tests/test_flows.py": FLOW_TEST_PY,
        }
        return {
            path: content.replace("__PACKAGE__", package).replace("__NAME__", spec.name)
            for path, content in files.items()
        }

    return FeatureSpec(
        name="prefect",
        directories={"src/{package}/flows": "Prefect flows"},
        dependencies=["prefect"],
        stack_notes=[f"Prefect: flows in `src/{package}/flows/`, deployments in `prefect.yaml`"],
        badges=["prefect"],
        testing_notes=["Prefect flows: unit-test the plain functions, not the flow runs"],
        commands={
            "Start Prefect server": "uv run prefect server start",
            "Run example flow": f"uv run python src/{package}/flows/hello.py",
            "Deploy flows": "uv run prefect deploy --all",
        },
        render_files=render_files,
    )
