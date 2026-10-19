"""dbt adapters supported by `--with-dbt`.

To support another warehouse (BigQuery, Snowflake, ...) add one entry to ADAPTERS:
the pip package, the `dev` output of profiles.yml, the environment variables it reads and
the badge key from ``kickoff.generators.badges.TOOL_BADGES``. Nothing else changes.

In ``profile`` and ``env_vars`` the token ``__PACKAGE__`` is replaced with the project's
package name. Profile lines are indented to sit under ``outputs: dev:``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DbtAdapter:
    package: str  # installed with `uv add`; it brings dbt-core with it
    maintainer: str  # shown in the README table
    badge: str  # key of TOOL_BADGES
    profile: str
    env_vars: dict[str, str] = field(default_factory=dict)
    notice: str | None = None  # printed as a warning when the adapter is selected


POSTGRES_PROFILE = """\
      type: postgres
      host: "{{ env_var('DBT_POSTGRES_HOST', 'localhost') }}"
      port: "{{ env_var('DBT_POSTGRES_PORT', '5432') | as_number }}"
      user: "{{ env_var('DBT_POSTGRES_USER') }}"
      password: "{{ env_var('DBT_POSTGRES_PASSWORD') }}"
      dbname: "{{ env_var('DBT_POSTGRES_DBNAME') }}"
      schema: "{{ env_var('DBT_POSTGRES_SCHEMA', 'public') }}"
      threads: 4
"""

DUCKDB_PROFILE = """\
      type: duckdb
      path: "{{ env_var('DBT_DUCKDB_PATH', 'data/processed/__PACKAGE__.duckdb') }}"
      threads: 4
"""

SQLITE_PROFILE = """\
      type: sqlite
      threads: 1
      database: __PACKAGE__
      schema: main
      schemas_and_paths:
        main: "{{ env_var('DBT_SQLITE_PATH', 'data/processed/__PACKAGE__.db') }}"
      schema_directory: "{{ env_var('DBT_SQLITE_DIR', 'data/processed') }}"
"""

ADAPTERS: dict[str, DbtAdapter] = {
    "postgres": DbtAdapter(
        package="dbt-postgres",
        maintainer="dbt Labs",
        badge="postgresql",
        profile=POSTGRES_PROFILE,
        env_vars={
            "DBT_POSTGRES_HOST": "localhost",
            "DBT_POSTGRES_PORT": "5432",
            "DBT_POSTGRES_USER": "__PACKAGE__",
            "DBT_POSTGRES_PASSWORD": "change-me",
            "DBT_POSTGRES_DBNAME": "__PACKAGE__",
            "DBT_POSTGRES_SCHEMA": "public",
        },
    ),
    "duckdb": DbtAdapter(
        package="dbt-duckdb",
        maintainer="community",
        badge="duckdb",
        profile=DUCKDB_PROFILE,
        env_vars={"DBT_DUCKDB_PATH": "data/processed/__PACKAGE__.duckdb"},
    ),
    "sqlite": DbtAdapter(
        package="dbt-sqlite",
        maintainer="community",
        badge="sqlite",
        profile=SQLITE_PROFILE,
        env_vars={
            "DBT_SQLITE_PATH": "data/processed/__PACKAGE__.db",
            "DBT_SQLITE_DIR": "data/processed",
        },
        notice=(
            "dbt-sqlite is a community plugin that dbt Labs does not support, and it can lag "
            "behind dbt-core. If `uv add` fails or dbt errors, try another adapter or Python 3.12."
        ),
    ),
}
