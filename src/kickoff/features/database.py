"""Database credentials derived from the project, shared by docker, Django and dbt."""

from __future__ import annotations

from dataclasses import dataclass

from kickoff.models import ProjectSpec

PLACEHOLDER_PASSWORD = "change-me"


@dataclass(frozen=True)
class DbCredentials:
    user: str
    password: str
    name: str
    host: str
    port: int


def has_database(spec: ProjectSpec) -> bool:
    return spec.db != "none"


def db_credentials(spec: ProjectSpec) -> DbCredentials:
    """User and database name come from the project name; the password from `--db-password`
    or, when kickoff runs, a random value (see `commands.new`).

    The host is as seen from your machine: the port is only published with `--expose-db`.
    """
    return DbCredentials(
        user=spec.package_name,
        password=spec.db_password or PLACEHOLDER_PASSWORD,
        name=spec.package_name,
        host="localhost",
        port=spec.db_port if spec.expose_db else 5432,
    )
