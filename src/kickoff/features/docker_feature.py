"""The docker feature (`--docker`, `--db`): Dockerfile, compose files and the database.

Generated layout:

- ``Dockerfile``: multi-stage, dependencies installed by uv, runs as a non-root user.
- ``docker-compose.yml``: ``db`` (and ``pgadmin``) start without a profile; ``app`` is under the
  ``full`` profile when there are such services, otherwise it starts by default.
- ``compose.override.yml``: development conveniences, loaded automatically by `docker compose`.
- ``.dockerignore``, ``docker/entrypoint.sh`` (templates that need start-up steps).
"""

from __future__ import annotations

import json

from kickoff import defaults
from kickoff.features.database import PLACEHOLDER_PASSWORD, db_credentials, has_database
from kickoff.features.services import AuxService, enabled_services
from kickoff.models import FeatureSpec, ProjectSpec, TemplateSpec

# Database name -> key of TOOL_BADGES.
DB_BADGES = {"postgres": "postgresql", "postgis": "postgis"}

DOCKERIGNORE = """\
.git/
.github/
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.env
.env.*
!.env.example
data/
outputs/
media/
staticfiles/
db.sqlite3
"""

MAIN_PY = '''\
"""Command-line entry point: `python -m __PACKAGE__`."""

import typer

app = typer.Typer()


@app.command()
def main() -> None:
    """Replace this with your application."""
    typer.echo("__NAME__ is running")


if __name__ == "__main__":
    app()
'''


def _format(parts: list[str], spec: ProjectSpec, template: TemplateSpec) -> list[str]:
    port = template.docker_config.container_port
    return [part.format(package=spec.package_name, port=port) for part in parts]


def container_commands(
    spec: ProjectSpec, template: TemplateSpec
) -> tuple[list[str], list[str] | None]:
    """Return the container CMD and the development CMD (None when it is the same)."""
    config = template.docker_config
    server = template.servers.get(spec.server)
    if server and server.docker_command:
        command, dev = server.docker_command, server.docker_dev_command
    else:
        command, dev = config.command, config.dev_command
    return _format(command, spec, template), (_format(dev, spec, template) if dev else None)


def system_packages(spec: ProjectSpec, template: TemplateSpec) -> list[str]:
    packages = list(template.docker_config.system_packages)
    if template.db_aware and spec.db == "postgis":
        packages.append("gdal-bin")  # Django's GIS support needs GDAL and GEOS
    return packages


def traefik_slug(spec: ProjectSpec) -> str:
    """Host-name safe project name (Django rejects underscores in host names)."""
    return spec.name.lower().replace("_", "-")


def traefik_host(spec: ProjectSpec, subdomain: str | None = None) -> str:
    base = f"{traefik_slug(spec)}.{spec.traefik_domain}"
    return f"{subdomain}.{base}" if subdomain else base


def _traefik_block(spec: ProjectSpec, router: str, host: str, port: int) -> list[str]:
    """Compose lines (service level) that route `host` through Traefik to `port`."""
    rule = f"traefik.http.routers.{router}"
    labels = [
        "traefik.enable=true",
        f"traefik.docker.network={spec.traefik_network}",
        f"{rule}.rule=Host(`{host}`)",
        f"{rule}.entrypoints={spec.traefik_entrypoint}",
        f"traefik.http.services.{router}.loadbalancer.server.port={port}",
    ]
    if spec.traefik_cert_resolver:
        labels += [f"{rule}.tls=true", f"{rule}.tls.certresolver={spec.traefik_cert_resolver}"]
    return [
        "    networks:",
        "      - default",
        "      - traefik",
        "    labels:",
        *[f'      - "{label}"' for label in labels],
    ]


def has_external_services(spec: ProjectSpec) -> bool:
    return has_database(spec) or spec.with_pgadmin or bool(enabled_services(spec))


def render_dockerfile(spec: ProjectSpec, template: TemplateSpec) -> str:
    config = template.docker_config
    command, _ = container_commands(spec, template)
    user = defaults.DOCKER_USER
    lines = [
        "# syntax=docker/dockerfile:1",
        f"ARG PYTHON_VERSION={spec.python_version}",
        "",
        "FROM python:${PYTHON_VERSION}-slim AS builder",
        f"COPY --from={defaults.UV_IMAGE} /uv /usr/local/bin/uv",
        "ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv",
        "WORKDIR /app",
        "COPY pyproject.toml uv.lock ./",
        "RUN --mount=type=cache,target=/root/.cache/uv \\",
        "    uv sync --frozen --no-dev --no-install-project",
        "",
        "FROM python:${PYTHON_VERSION}-slim AS runtime",
    ]
    packages = system_packages(spec, template)
    if packages:
        lines += [
            "RUN apt-get update \\",
            f"    && apt-get install -y --no-install-recommends {' '.join(packages)} \\",
            "    && rm -rf /var/lib/apt/lists/*",
        ]
    lines += [
        f"RUN groupadd --system {user} && useradd --system --gid {user} --home-dir /app {user}",
        'ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \\',
        "    PYTHONPATH=/app/src",
        "WORKDIR /app",
        f"RUN chown {user}:{user} /app",
        "COPY --from=builder /opt/venv /opt/venv",
        f"COPY --chown={user}:{user} . .",
        f"USER {user}",
        f"EXPOSE {config.container_port}",
    ]
    if config.entrypoint_steps:
        lines.append('ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]')
    if config.healthcheck_path:
        url = f"http://127.0.0.1:{config.container_port}{config.healthcheck_path}"
        lines += [
            "HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \\",
            f'    CMD python -c "import urllib.request; urllib.request.urlopen(\'{url}\')"',
        ]
    lines.append(f"CMD {json.dumps(command)}")
    return "\n".join(lines) + "\n"


def render_entrypoint(template: TemplateSpec) -> str:
    steps = "\n".join(template.docker_config.entrypoint_steps)
    return f'#!/bin/sh\nset -e\n\n{steps}\n\nexec "$@"\n'


def _aux_lines(spec: ProjectSpec, service: AuxService) -> list[str]:
    lines = [f"  {service.name}:", f"    image: {service.image}"]
    lines += [f"    {line}" for line in service.lines]
    if spec.traefik and service.ui:
        subdomain, port = service.ui
        router = f"{traefik_slug(spec)}-{service.name}"
        lines += _traefik_block(spec, router, traefik_host(spec, subdomain), port)
    return [*lines, ""]


def _app_environment(spec: ProjectSpec, services: list[AuxService]) -> dict[str, str]:
    """Variables that differ inside the app container: services are reached by name."""
    env: dict[str, str] = {}
    if has_database(spec):
        env.update(POSTGRES_HOST="db", POSTGRES_PORT="5432")
    for service in services:
        env.update(service.app_env)
    return env


def render_compose(spec: ProjectSpec, template: TemplateSpec) -> str:
    config = template.docker_config
    has_db = has_database(spec)
    services = enabled_services(spec)
    lines = [f"name: {spec.package_name}", "", "services:"]

    if has_db:
        lines += [
            "  db:",
            f"    image: {defaults.DB_IMAGES[spec.db]}",
            "    env_file: .env",
            "    volumes:",
            "      - pgdata:/var/lib/postgresql/data",
            "    expose:",
            '      - "5432"',
        ]
        if spec.expose_db:
            # Bound to loopback: reachable from DBeaver and friends, not from the local network.
            lines += ["    ports:", '      - "127.0.0.1:${DB_PORT:-5432}:5432"']
        lines += [
            "    healthcheck:",
            '      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]',
            "      interval: 5s",
            "      timeout: 5s",
            "      retries: 10",
            "",
        ]
    if spec.with_pgadmin:
        lines += [
            "  pgadmin:",
            f"    image: {defaults.PGADMIN_IMAGE}",
            "    env_file: .env",
            "    depends_on:",
            "      db:",
            "        condition: service_healthy",
            "    volumes:",
            "      - pgadmin:/var/lib/pgadmin",
        ]
        if spec.traefik:
            router = f"{traefik_slug(spec)}-pgadmin"
            lines += _traefik_block(spec, router, traefik_host(spec, "pgadmin"), 80)
        lines.append("")
    for service in services:
        lines += _aux_lines(spec, service)

    lines.append("  app:")
    if has_external_services(spec):
        lines.append("    profiles: [full]")
    lines += ["    build: .", "    env_file: .env"]
    environment = _app_environment(spec, services)
    if environment:
        lines.append("    environment:")
        lines += [f'      {key}: "{value}"' for key, value in environment.items()]
    depends = ([("db", True)] if has_db else []) + [(s.name, s.healthy) for s in services]
    if depends:
        lines.append("    depends_on:")
        for name, healthy in depends:
            condition = "service_healthy" if healthy else "service_started"
            lines += [f"      {name}:", f"        condition: {condition}"]
    if spec.traefik:
        # Reached through Traefik; no host port, so projects never fight over 8000.
        router = traefik_slug(spec)
        lines += _traefik_block(spec, router, traefik_host(spec), config.container_port)
    else:
        lines += [
            "    ports:",
            f'      - "${{APP_PORT:-{spec.app_port}}}:{config.container_port}"',
        ]

    volumes = [
        *(["pgdata"] if has_db else []),
        *(["pgadmin"] if spec.with_pgadmin else []),
        *[volume for service in services for volume in service.volumes],
    ]
    if volumes:
        lines += ["", "volumes:", *[f"  {name}:" for name in volumes]]
    if spec.traefik:
        lines += [
            "",
            "networks:",
            "  traefik:",
            f"    name: {spec.traefik_network}",
            "    external: true",
        ]
    return "\n".join(lines) + "\n"


def render_override(spec: ProjectSpec, template: TemplateSpec) -> str:
    _, dev_command = container_commands(spec, template)
    lines = [
        "# Development settings, loaded automatically by `docker compose`.",
        "# Production: docker compose -f docker-compose.yml up",
        "services:",
        "  app:",
        "    # Bind-mounted files keep the host's ownership, so run as root in development.",
        "    user: root",
        "    volumes:",
        "      - .:/app",
    ]
    if dev_command:
        lines.append(f"    command: {json.dumps(dev_command)}")
    lines += ["    ports:", '      - "127.0.0.1:${DEBUG_PORT:-5678}:5678"']
    if spec.with_pgadmin:
        lines += [
            "",
            "  pgadmin:",
            "    ports:",
            f'      - "127.0.0.1:${{PGADMIN_PORT:-{defaults.PGADMIN_PORT}}}:80"',
        ]
    for service in enabled_services(spec):
        if service.dev_ports:
            lines += ["", f"  {service.name}:", "    ports:"]
            lines += [
                f'      - "127.0.0.1:${{{variable}:-{host}}}:{container}"'
                for variable, host, container in service.dev_ports
            ]
    return "\n".join(lines) + "\n"


def render_skill(spec: ProjectSpec) -> str:
    has_db = has_database(spec)
    aux = enabled_services(spec)
    names = [*(["db"] if has_db else []), *(["pgadmin"] if spec.with_pgadmin else [])]
    services = " and ".join([*names, *[service.name for service in aux]])
    lines = [
        "---",
        "name: docker-workflow",
        "description: Run the project and its services with Docker Compose",
        "---",
        "# Docker Workflow",
        "",
    ]
    if has_external_services(spec):
        lines += [
            f"- Start the services ({services}): `docker compose up -d`",
            "- Start everything, including the app (profile `full`): "
            "`docker compose --profile full up --build`",
        ]
        if has_db:
            lines.append(
                "- Database shell: "
                "`docker compose exec db sh -c 'psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"'`"
            )
    else:
        lines.append("- Build and start the app: `docker compose up --build`")
    lines += [
        "- Logs: `docker compose logs -f`",
        "- Stop: `docker compose down` (add `-v` to also delete the database volume)",
        "",
        "## Ports",
        "",
        (
            f"- App: https://{traefik_host(spec)} through Traefik (no host port)"
            if spec.traefik
            else f"- App: http://localhost:{spec.app_port} (change `APP_PORT` in `.env`)"
        ),
    ]
    if has_db:
        expose = (
            f"published on 127.0.0.1:{spec.db_port} (`DB_PORT` in `.env`)"
            if spec.expose_db
            else "not published on the host; other containers reach it as `db:5432`"
        )
        lines.append(f"- Database: {expose}")
    if spec.with_pgadmin:
        lines.append(f"- pgAdmin: http://127.0.0.1:{defaults.PGADMIN_PORT} in development only")
    for service in aux:
        ports = ", ".join(
            f"{variable}={host}" for variable, host, _ in service.dev_ports
        )
        reach = f"; development ports on 127.0.0.1 ({ports})" if ports else ""
        lines.append(f"- {service.name}: reached by other containers as `{service.name}`{reach}")
    if spec.traefik:
        lines += [
            "",
            "## Traefik",
            "",
            f"- Join the external network `{spec.traefik_network}` (create it once: "
            f"`docker network create {spec.traefik_network}`) and attach your Traefik to it.",
            f"- Entry point `{spec.traefik_entrypoint}`, domain `{spec.traefik_domain}`.",
        ]
    lines += [
        "",
        "`compose.override.yml` is for development (code mounted, reload, debug port) and is "
        "loaded automatically. Never commit `.env`.",
    ]
    return "\n".join(lines) + "\n"


def _environment(
    spec: ProjectSpec, template: TemplateSpec
) -> tuple[dict[str, str], dict[str, str]]:
    env = {"APP_PORT": str(spec.app_port)}
    examples: dict[str, str] = {}
    if has_database(spec):
        creds = db_credentials(spec)
        env.update(
            POSTGRES_USER=creds.user,
            POSTGRES_PASSWORD=creds.password,
            POSTGRES_DB=creds.name,
            POSTGRES_HOST=creds.host,
            POSTGRES_PORT=str(creds.port),
        )
        examples["POSTGRES_PASSWORD"] = PLACEHOLDER_PASSWORD
        if spec.expose_db:
            env["DB_PORT"] = str(spec.db_port)
    if spec.with_pgadmin:
        env.update(
            PGADMIN_DEFAULT_EMAIL=defaults.PGADMIN_EMAIL,
            PGADMIN_DEFAULT_PASSWORD=defaults.ENV_SECRET,
            PGADMIN_PORT=str(defaults.PGADMIN_PORT),
        )
    for service in enabled_services(spec):
        for name, value in service.env.items():
            env[name] = value.replace("__PACKAGE__", spec.package_name)
        env.update({variable: str(host) for variable, host, _ in service.dev_ports})
    env["DEBUG_PORT"] = str(defaults.DEBUG_PORT)
    env.update(template.docker_config.env)
    if spec.traefik and "DJANGO_ALLOWED_HOSTS" in template.env_vars:
        host = traefik_host(spec)
        env["DJANGO_ALLOWED_HOSTS"] = f"{template.env_vars['DJANGO_ALLOWED_HOSTS']},{host}"
        env["DJANGO_CSRF_TRUSTED_ORIGINS"] = f"http://{host},https://{host}"
    return env, examples


def docker_feature(spec: ProjectSpec, template: TemplateSpec) -> FeatureSpec:
    has_db = has_database(spec)
    config = template.docker_config
    env, examples = _environment(spec, template)

    def render_files(_spec: ProjectSpec) -> dict[str, str]:
        files = {
            "Dockerfile": render_dockerfile(spec, template),
            "docker-compose.yml": render_compose(spec, template),
            "compose.override.yml": render_override(spec, template),
            ".dockerignore": DOCKERIGNORE,
        }
        if config.entrypoint_steps:
            files["docker/entrypoint.sh"] = render_entrypoint(template)
        if config.main_module:
            files[f"src/{spec.package_name}/__main__.py"] = MAIN_PY.replace(
                "__PACKAGE__", spec.package_name
            ).replace("__NAME__", spec.name)
        if spec.enable_opencode:
            files[".opencode/skills/docker-workflow/SKILL.md"] = render_skill(spec)
        return files

    commands = {
        "Start services (Docker)": "docker compose up -d",
        "Start everything (Docker)": "docker compose --profile full up --build",
        "Stop (Docker)": "docker compose down",
    }
    if not has_db:
        commands = {
            "Start app (Docker)": "docker compose up --build",
            "Stop (Docker)": "docker compose down",
        }

    aux = enabled_services(spec)
    services = [
        "app",
        *(["db"] if has_db else []),
        *(["pgadmin"] if spec.with_pgadmin else []),
        *[service.name for service in aux],
    ]
    notices = []
    if spec.with_minio:
        notices.append(
            "MinIO's own images were withdrawn in 2026; the object store runs "
            f"{spec.minio_image} (Silo, a maintained drop-in fork). Change docker.minio_image "
            "in the kickoff config to use another image."
        )
    if spec.traefik:
        notices.append(
            f"Traefik: create the external network once with `docker network create "
            f"{spec.traefik_network}` and attach your Traefik to it. kickoff does not run Traefik."
        )
    if template.db_aware and spec.db == "postgis":
        notices.append(
            "Django + PostGIS needs GDAL and GEOS. They are installed in the Docker image and in "
            "CI; install them on your machine too to run Django outside Docker."
        )
    return FeatureSpec(
        name="docker",
        dependencies=[
            *(["psycopg[binary]"] if (has_db and template.db_aware) else []),
            *[dep for service in aux for dep in service.dependencies],
        ],
        gitignore_extra=[],
        stack_notes=[f"Docker Compose services: {', '.join(services)}"],
        notices=notices,
        env_vars=env,
        env_examples=examples,
        badges=[
            "docker",
            *([DB_BADGES[spec.db]] if has_db else []),
            *[service.badge for service in aux if service.badge],
            *(["traefik"] if spec.traefik else []),
        ],
        commands=commands,
        render_files=render_files,
    )
