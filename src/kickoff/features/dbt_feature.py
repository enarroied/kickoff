"""The `--with-dbt` feature: a dbt project in `dbt/` plus the chosen adapter."""

from __future__ import annotations

from kickoff.features.database import db_credentials, has_database
from kickoff.features.dbt_adapters import ADAPTERS
from kickoff.models import FeatureSpec, ProjectSpec, TemplateSpec

DBT_PROJECT_YML = """\
name: "__PACKAGE__"
version: "1.0.0"
profile: "__PACKAGE__"

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

clean-targets: ["target", "dbt_packages"]

models:
  __PACKAGE__:
    +materialized: view
"""

# Contains no secrets: every credential comes from an environment variable (see .env).
PROFILES_YML = """\
__PACKAGE__:
  target: dev
  outputs:
    dev:
__PROFILE__"""

EXAMPLE_MODEL_SQL = """\
-- Example model: replace it with your own.
select 1 as id
"""

SCHEMA_YML = """\
version: 2

models:
  - name: example
    description: "Example model: replace it with your own."
    columns:
      - name: id
        description: "Primary key"
        tests:
          - unique
          - not_null
"""

DBT_DIRECTORIES = {
    "dbt": "dbt project (models, seeds, macros)",
    "dbt/models": "",
    "dbt/analyses": "",
    "dbt/macros": "",
    "dbt/seeds": "",
    "dbt/snapshots": "",
    "dbt/tests": "",
}

# dbt is always run from the repository root with explicit directories.
DBT_FLAGS = "--project-dir dbt --profiles-dir dbt"


def dbt_feature(spec: ProjectSpec, _template: TemplateSpec) -> FeatureSpec:
    adapter = ADAPTERS[spec.dbt_adapter]
    package = spec.package_name

    def render_files(_spec: ProjectSpec) -> dict[str, str]:
        profiles = PROFILES_YML.replace("__PROFILE__", adapter.profile)
        files = {
            "dbt/dbt_project.yml": DBT_PROJECT_YML,
            "dbt/profiles.yml": profiles,
            "dbt/models/example.sql": EXAMPLE_MODEL_SQL,
            "dbt/models/schema.yml": SCHEMA_YML,
        }
        return {path: content.replace("__PACKAGE__", package) for path, content in files.items()}

    env_vars = {
        name: value.replace("__PACKAGE__", package) for name, value in adapter.env_vars.items()
    }
    env_examples: dict[str, str] = {}
    if spec.dbt_adapter == "postgres" and has_database(spec):
        # Point dbt at the database that docker compose creates for this project.
        creds = db_credentials(spec)
        env_vars.update(
            DBT_POSTGRES_HOST=creds.host,
            DBT_POSTGRES_PORT=str(creds.port),
            DBT_POSTGRES_USER=creds.user,
            DBT_POSTGRES_PASSWORD=creds.password,
            DBT_POSTGRES_DBNAME=creds.name,
        )
        env_examples["DBT_POSTGRES_PASSWORD"] = "change-me"

    return FeatureSpec(
        name="dbt",
        directories=DBT_DIRECTORIES,
        dependencies=[adapter.package],
        gitignore_extra=["dbt/target/", "dbt/dbt_packages/", "dbt/logs/", "dbt/.user.yml"],
        stack_notes=[
            f"dbt with the {spec.dbt_adapter} adapter: project in `dbt/`, "
            "run dbt from the repository root"
        ],
        notices=[adapter.notice] if adapter.notice else [],
        env_vars=env_vars,
        env_examples=env_examples,
        badges=["dbt", adapter.badge],
        commands={
            "dbt debug": f"uv run --env-file .env dbt debug {DBT_FLAGS}",
            "dbt build": f"uv run --env-file .env dbt build {DBT_FLAGS}",
        },
        render_files=render_files,
    )
