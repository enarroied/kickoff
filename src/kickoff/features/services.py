"""Auxiliary Docker services: Redis, MinIO (Silo) and Mailpit.

To add another service, add one `AuxService` to SERVICES and a `with_<name>` field to
`ProjectSpec` plus a CLI flag; the Docker feature renders everything else.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kickoff import defaults
from kickoff.models import ProjectSpec


@dataclass(frozen=True)
class AuxService:
    """One extra compose service."""

    name: str  # compose service name
    image: str
    lines: tuple[str, ...]  # compose lines below `image:`, written for a 4-space indent
    volumes: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)  # `.env`: how code on your machine sees it
    app_env: dict[str, str] = field(default_factory=dict)  # overrides inside the app container
    dev_ports: tuple[tuple[str, int, int], ...] = ()  # (variable, host port, container port)
    ui: tuple[str, int] | None = None  # (Traefik subdomain, container port) of a web UI
    dependencies: tuple[str, ...] = ()  # pip packages the app needs to talk to it
    badge: str | None = None  # key of TOOL_BADGES
    healthy: bool = False  # the app waits for the healthcheck, otherwise just for the start


def redis_service(_spec: ProjectSpec) -> AuxService:
    return AuxService(
        name="redis",
        image=defaults.REDIS_IMAGE,
        lines=(
            "volumes:",
            "  - redis:/data",
            "healthcheck:",
            '  test: ["CMD", "redis-cli", "ping"]',
            "  interval: 5s",
            "  timeout: 3s",
            "  retries: 10",
        ),
        volumes=("redis",),
        env={"REDIS_URL": "redis://localhost:6379/0"},
        app_env={"REDIS_URL": "redis://redis:6379/0"},
        dev_ports=(("REDIS_PORT", 6379, 6379),),
        dependencies=("redis",),
        badge="redis",
        healthy=True,
    )


def minio_service(spec: ProjectSpec) -> AuxService:
    return AuxService(
        name="minio",
        image=spec.minio_image,
        lines=(
            "env_file: .env",
            'command: ["server", "/data", "--console-address", ":9001"]',
            "volumes:",
            "  - minio:/data",
            "healthcheck:",
            '  test: ["CMD", "mc", "ready", "local"]',
            "  interval: 10s",
            "  timeout: 5s",
            "  retries: 10",
        ),
        volumes=("minio",),
        env={
            "MINIO_ROOT_USER": "__PACKAGE__",
            "MINIO_ROOT_PASSWORD": defaults.ENV_SECRET,
            "MINIO_ENDPOINT": "localhost:9000",
        },
        app_env={"MINIO_ENDPOINT": "minio:9000"},
        dev_ports=(("MINIO_API_PORT", 9000, 9000), ("MINIO_CONSOLE_PORT", 9001, 9001)),
        ui=("minio", 9001),
        dependencies=("minio",),
        badge="minio",
    )


def mailpit_service(_spec: ProjectSpec) -> AuxService:
    return AuxService(
        name="mailpit",
        image=defaults.MAILPIT_IMAGE,
        lines=(),
        env={"MAIL_HOST": "localhost"},
        app_env={"MAIL_HOST": "mailpit"},
        dev_ports=(("MAIL_PORT", 1025, 1025), ("MAIL_UI_PORT", 8025, 8025)),
        ui=("mail", 8025),
        badge="mailpit",
    )


# Flag name (ProjectSpec.with_<key>) -> factory.
SERVICES = {
    "redis": redis_service,
    "minio": minio_service,
    "mail": mailpit_service,
}


def enabled_services(spec: ProjectSpec) -> list[AuxService]:
    return [factory(spec) for key, factory in SERVICES.items() if getattr(spec, f"with_{key}")]
